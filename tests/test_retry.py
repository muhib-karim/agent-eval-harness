import asyncio
import json
import random
import time
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

import httpx
import pytest
import yaml
from pydantic import ValidationError

from agent_eval import runners
from agent_eval.cli import main
from agent_eval.engine import recover_attempts, run_config
from agent_eval.report import render_report
from agent_eval.results import Attempt, load_attempts, summarize
from agent_eval.retry import (
    RetryError,
    RetryPolicy,
    Transient,
    backoff_delays,
    delay_for,
    resolve_policy,
    with_retries,
)
from agent_eval.runners.base import Runner, RunnerError
from agent_eval.runners.http import HTTPRunner, classify_http_error, parse_retry_after
from agent_eval.specs import load_task

BASE = str(httpx.URL(scheme="https", host="endpoint.invalid", path="/v1"))
REQUEST = httpx.Request("POST", BASE + "/chat/completions")
REPLY = {
    "choices": [{"message": {"content": "```python\ndef answer():\n    return 42\n```"}}],
    "usage": {"prompt_tokens": 10, "completion_tokens": 20},
}


class Sleeps:
    """Records requested waits instead of sleeping."""

    def __init__(self) -> None:
        self.delays: list[float] = []

    async def __call__(self, delay: float) -> None:
        self.delays.append(delay)


def status_error(status: int, headers: dict[str, str] | None = None) -> httpx.HTTPStatusError:
    response = httpx.Response(status, headers=headers, text="secret body", request=REQUEST)
    return httpx.HTTPStatusError("secret", request=REQUEST, response=response)


def test_backoff_without_jitter_grows_exponentially_up_to_the_cap() -> None:
    policy = RetryPolicy(max_retries=7, jitter="none")
    assert backoff_delays(policy, random.Random(0)) == [1, 2, 4, 8, 16, 30, 30]
    policy = RetryPolicy(
        max_retries=4, base_delay_s=0.5, multiplier=3, max_delay_s=10, jitter="none"
    )
    assert backoff_delays(policy, random.Random(0)) == [0.5, 1.5, 4.5, 10]
    assert backoff_delays(RetryPolicy(max_retries=0), random.Random(0)) == []


def test_full_jitter_stays_within_the_exponential_ceiling() -> None:
    policy = RetryPolicy(max_retries=10)
    first = backoff_delays(policy, random.Random(7))
    assert first == backoff_delays(policy, random.Random(7))
    ceilings = backoff_delays(policy.model_copy(update={"jitter": "none"}), random.Random(0))
    assert all(0 <= delay <= ceiling for delay, ceiling in zip(first, ceilings, strict=True))
    assert first != ceilings
    samples = [delay_for(9, policy, random.Random(seed)) for seed in range(200)]
    assert max(samples) <= 30 and min(samples) < 5


def test_policy_defaults_and_bounds() -> None:
    policy = RetryPolicy()
    assert (policy.max_retries, policy.base_delay_s, policy.max_delay_s) == (3, 1.0, 30.0)
    assert (policy.multiplier, policy.jitter) == (2.0, "full")
    for bad in ({"max_retries": 11}, {"max_retries": -1}, {"base_delay_s": -1}, {"x": 1}):
        with pytest.raises(ValidationError):
            RetryPolicy.model_validate(bad)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("5", 5.0),
        (" 2.5 ", 2.5),
        ("0", 0.0),
        ("Wed, 21 Oct 2015 07:28:00 GMT", None),
        ("-1", None),
        ("", None),
        (None, None),
    ],
)
def test_parse_retry_after(value: str | None, expected: float | None) -> None:
    assert parse_retry_after(value) == expected


@pytest.mark.parametrize("status", [408, 409, 425, 429, 500, 502, 503, 504, 529])
def test_transient_statuses(status: int) -> None:
    assert classify_http_error(status_error(status)) == Transient(f"http_{status}")


def test_retry_after_is_read_from_transient_responses() -> None:
    assert classify_http_error(status_error(429, {"Retry-After": "7"})) == Transient("http_429", 7)
    dated = status_error(503, {"Retry-After": "Wed, 21 Oct 2015 07:28:00 GMT"})
    assert classify_http_error(dated) == Transient("http_503")


@pytest.mark.parametrize(
    "error",
    [
        httpx.ConnectError("secret", request=REQUEST),
        httpx.ReadError("secret", request=REQUEST),
        httpx.RemoteProtocolError("secret", request=REQUEST),
        httpx.ConnectTimeout("secret", request=REQUEST),
        httpx.ReadTimeout("secret", request=REQUEST),
        httpx.PoolTimeout("secret", request=REQUEST),
    ],
)
def test_transient_transport_errors(error: Exception) -> None:
    assert classify_http_error(error) == Transient(type(error).__name__)


@pytest.mark.parametrize(
    "error",
    [
        *(status_error(status) for status in (400, 401, 403, 404, 422)),
        httpx.WriteTimeout("secret", request=REQUEST),
        httpx.UnsupportedProtocol("secret", request=REQUEST),
        TimeoutError(),
        ValueError("invalid response"),
        RunnerError("required API environment variable is missing"),
        RunnerError("model returned empty code"),
    ],
)
def test_non_transient_errors(error: Exception) -> None:
    assert classify_http_error(error) is None


def flaky(failures: list[Exception], result: str = "ok") -> Any:
    remaining = list(failures)

    async def call() -> str:
        if remaining:
            raise remaining.pop(0)
        return result

    return call


def classify(exc: Exception) -> Transient | None:
    return Transient(str(exc)) if isinstance(exc, ConnectionError) else None


def test_with_retries_succeeds_after_transient_failures() -> None:
    sleeps = Sleeps()
    policy = RetryPolicy(jitter="none")
    call = flaky([ConnectionError("a"), ConnectionError("b")])
    result = asyncio.run(
        with_retries(call, policy, classify=classify, sleep=sleeps, rng=random.Random(0))
    )
    assert result == ("ok", ["a", "b"])
    assert sleeps.delays == [1, 2]


def test_with_retries_exhaustion_carries_every_reason() -> None:
    sleeps = Sleeps()
    call = flaky([ConnectionError(str(n)) for n in range(5)])
    with pytest.raises(RetryError) as caught:
        asyncio.run(with_retries(call, RetryPolicy(max_retries=2), classify=classify, sleep=sleeps))
    assert caught.value.reasons == ["0", "1"]
    assert str(caught.value.error) == "2"
    assert len(sleeps.delays) == 2


def test_with_retries_stops_at_a_non_transient_failure() -> None:
    sleeps = Sleeps()
    call = flaky([ConnectionError("a"), KeyError("bad")])
    with pytest.raises(RetryError) as caught:
        asyncio.run(with_retries(call, RetryPolicy(), classify=classify, sleep=sleeps))
    assert caught.value.reasons == ["a"]
    assert isinstance(caught.value.error, KeyError)


def test_zero_retries_fails_immediately() -> None:
    sleeps = Sleeps()
    with pytest.raises(RetryError) as caught:
        asyncio.run(
            with_retries(
                flaky([ConnectionError("a")]),
                RetryPolicy(max_retries=0),
                classify=classify,
                sleep=sleeps,
            )
        )
    assert caught.value.reasons == [] and sleeps.delays == []


@pytest.mark.parametrize("retry_after,expected", [(2.0, 2.0), (120.0, 30.0), (0.0, 0.0)])
def test_retry_after_overrides_backoff_but_not_the_cap(retry_after: float, expected: float) -> None:
    sleeps = Sleeps()
    remaining = [ConnectionError("x")]

    async def call() -> str:
        if remaining:
            raise remaining.pop()
        return "ok"

    asyncio.run(
        with_retries(
            call,
            RetryPolicy(jitter="none", base_delay_s=9),
            classify=lambda exc: Transient("http_429", retry_after),
            sleep=sleeps,
        )
    )
    assert sleeps.delays == [expected]


def test_resolve_policy_precedence() -> None:
    base = RetryPolicy(max_retries=5, base_delay_s=4)
    assert resolve_policy(base) == base
    model = resolve_policy(base, RetryPolicy(max_retries=1))
    assert (model.max_retries, model.base_delay_s) == (1, 4)
    flag = resolve_policy(base, RetryPolicy(max_retries=1), max_retries=0)
    assert (flag.max_retries, flag.base_delay_s) == (0, 4)
    with pytest.raises(ValidationError):
        resolve_policy(base, max_retries=11)


def sequenced(statuses: list[int], requests: list[int]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(1)
        if len(requests) <= len(statuses):
            return httpx.Response(statuses[len(requests) - 1], text="secret body")
        return httpx.Response(200, json=REPLY)

    return httpx.MockTransport(handler)


def test_http_runner_keeps_usage_and_reasons_when_extraction_fails(
    task_path: Path, workdir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TEST_KEY", "fixture-key")
    monkeypatch.setenv("TEST_BASE", BASE)
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(502)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "```json\n{}\n```"}}], "usage": {}},
        )

    runner = HTTPRunner(
        {"model": "m", "base_url_env": "TEST_BASE", "api_key_env": "TEST_KEY"},
        transport=httpx.MockTransport(handler),
        sleep=Sleeps(),
    )
    with pytest.raises(RunnerError) as caught:
        asyncio.run(runner.generate(load_task(task_path), workdir))
    assert caught.value.retry_reasons == ("http_502",)
    assert "Python" in str(caught.value)


def test_http_runner_reraises_unexpected_errors_unretried(
    task_path: Path, workdir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TEST_KEY", "fixture-key")
    monkeypatch.setenv("TEST_BASE", BASE)

    def handler(request: httpx.Request) -> httpx.Response:
        raise RuntimeError("bug")

    runner = HTTPRunner(
        {"model": "m", "base_url_env": "TEST_BASE", "api_key_env": "TEST_KEY"},
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(RuntimeError):
        asyncio.run(runner.generate(load_task(task_path), workdir))


@pytest.fixture
def http_config(
    task_path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, list[int], Sleeps, list[int]]:
    """A one-attempt HTTP run; tests set the status sequence and read requests and sleeps."""
    monkeypatch.setenv("TEST_KEY", "fixture-key")
    monkeypatch.setenv("TEST_BASE", BASE)
    statuses: list[int] = []
    requests: list[int] = []
    sleeps = Sleeps()

    def factory(options: dict[str, Any], *, task_path: Path) -> Runner:
        return HTTPRunner(options, transport=sequenced(statuses, requests), sleep=sleeps)

    monkeypatch.setitem(runners._REGISTRY, "openai", factory)
    path = tmp_path / "http.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "models": [
                    {
                        "name": "http",
                        "runner": "openai",
                        "options": {
                            "model": "m",
                            "base_url_env": "TEST_BASE",
                            "api_key_env": "TEST_KEY",
                        },
                    }
                ],
                "tasks": [str(task_path.relative_to(tmp_path))],
                "retry": {"jitter": "none", "base_delay_s": 0.5},
            }
        )
    )
    return path, statuses, sleeps, requests


def test_http_run_records_retries_on_a_successful_attempt(
    http_config: tuple[Path, list[int], Sleeps, list[int]], tmp_path: Path
) -> None:
    path, statuses, sleeps, requests = http_config
    statuses.extend([429, 503])
    out = tmp_path / "run"
    [attempt] = asyncio.run(run_config(path, out))
    assert attempt.outcome == "pass"
    assert attempt.retries == 2 and attempt.retry_reasons == ["http_429", "http_503"]
    assert (attempt.input_tokens, attempt.output_tokens) == (10, 20)
    assert sleeps.delays == [0.5, 1.0] and len(requests) == 3
    row = json.loads((out / "results.jsonl").read_text())
    assert row["retries"] == 2 and row["retry_reasons"] == ["http_429", "http_503"]
    assert "secret body" not in (out / "results.jsonl").read_text()
    assert json.loads((out / "summary.json").read_text())["models"][0]["retries"] == 2
    assert "Retries after transient provider errors: http 2." in render_report(
        summarize([attempt]), "md"
    )
    assert "http 2" in (out / "report.html").read_text()
    assert "retry:" in (out / "config.resolved.yaml").read_text()


def test_http_run_records_retries_on_an_exhausted_attempt(
    http_config: tuple[Path, list[int], Sleeps, list[int]], tmp_path: Path
) -> None:
    path, statuses, sleeps, requests = http_config
    statuses.extend([503] * 10)
    [attempt] = asyncio.run(run_config(path, tmp_path / "run"))
    assert attempt.outcome == "error"
    assert attempt.error == "API request failed with HTTP 503"
    assert attempt.retry_reasons == ["http_503"] * 3 and attempt.retries == 3
    assert len(requests) == 4


def test_per_model_retry_overrides_the_config(
    http_config: tuple[Path, list[int], Sleeps, list[int]], tmp_path: Path
) -> None:
    path, statuses, sleeps, requests = http_config
    config = yaml.safe_load(path.read_text())
    config["retry"]["max_retries"] = 5
    config["models"][0]["options"]["retry"] = {"max_retries": 1}
    path.write_text(yaml.safe_dump(config))
    statuses.extend([503] * 10)
    [attempt] = asyncio.run(run_config(path, tmp_path / "run"))
    # max_retries comes from the model; base_delay_s and jitter still from the config.
    assert attempt.retries == 1 and sleeps.delays == [0.5] and len(requests) == 2


def test_max_retries_flag_overrides_config_and_model(
    http_config: tuple[Path, list[int], Sleeps, list[int]],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path, statuses, sleeps, requests = http_config
    config = yaml.safe_load(path.read_text())
    config["models"][0]["options"]["retry"] = {"max_retries": 4}
    path.write_text(yaml.safe_dump(config))
    statuses.extend([429] * 10)
    out = tmp_path / "run"
    assert main(["run", str(path), "--out", str(out), "--max-retries", "0"]) == 0
    [attempt] = load_attempts(out / "results.jsonl")
    assert attempt.outcome == "error" and attempt.retries == 0 and len(requests) == 1
    capsys.readouterr()
    assert main(["run", str(path), "--out", str(tmp_path / "bad"), "--max-retries", "11"]) == 2
    assert "max_retries" in capsys.readouterr().err
    assert not (tmp_path / "bad").exists()


def test_mock_and_cli_runners_are_not_retried(config_path: Path, tmp_path: Path) -> None:
    attempts = asyncio.run(run_config(config_path, tmp_path / "run", max_retries=5))
    assert all(row.retries == 0 and row.retry_reasons == [] for row in attempts)
    # Configs without a retry block resolve as before, so older runs stay resumable.
    assert "retry" not in (tmp_path / "run" / "config.resolved.yaml").read_text()


OLD_ROW = {
    "schema_version": "1.0",
    "attempt_id": "attempt-000001",
    "model": "old",
    "runner": "openai",
    "task_id": "answer",
    "repeat": 1,
    "outcome": "error",
    "wall_time_s": 1.0,
    "generation_time_s": 1.0,
    "grading_time_s": 0.0,
    "error": "API request failed with HTTP 429",
    "artifacts": "attempts/attempt-000001",
}


def test_old_rows_without_retry_fields_load_resume_and_report(tmp_path: Path) -> None:
    path = tmp_path / "results.jsonl"
    path.write_text(json.dumps(OLD_ROW) + "\n")
    [loaded] = load_attempts(path)
    assert loaded.retries == 0 and loaded.retry_reasons == []
    assert recover_attempts(path) == [loaded]
    summary = summarize([loaded])
    assert summary.models[0].retries == 0
    assert "Retries after transient provider errors: old 0." in render_report(summary, "md")
    assert '"retries": 0' in render_report(summary, "json")
    assert "old 0" in render_report(summary, "html")


def test_retry_count_must_match_reasons() -> None:
    with pytest.raises(ValidationError):
        Attempt.model_validate({**OLD_ROW, "retries": 2, "retry_reasons": ["http_429"]})


def test_http_runner_keeps_reasons_when_an_unexpected_error_follows_retries(
    http_config: tuple[Path, list[int], Sleeps, list[int]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path, statuses, sleeps, requests = http_config
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503, text="secret body")
        raise RuntimeError("secret bug")

    def factory(options: dict[str, Any], *, task_path: Path) -> Runner:
        return HTTPRunner(options, transport=httpx.MockTransport(handler), sleep=sleeps)

    monkeypatch.setitem(runners._REGISTRY, "openai", factory)
    out = tmp_path / "run"
    [attempt] = asyncio.run(run_config(path, out))
    assert attempt.outcome == "error" and attempt.error == "attempt failed: RuntimeError"
    assert attempt.retries == 1 and attempt.retry_reasons == ["http_503"]
    row = json.loads((out / "results.jsonl").read_text())
    assert row["retries"] == 1 and row["retry_reasons"] == ["http_503"]
    assert "secret" not in (out / "results.jsonl").read_text()


def interrupt(out: Path) -> None:
    """Drop the last recorded attempt, as if the run had died before writing it."""
    lines = (out / "results.jsonl").read_text().splitlines(keepends=True)
    (out / "results.jsonl").write_text("".join(lines[:-1]))


def test_resume_must_repeat_the_max_retries_flag(
    http_config: tuple[Path, list[int], Sleeps, list[int]], tmp_path: Path
) -> None:
    path, statuses, sleeps, requests = http_config
    statuses.extend([429] * 10)
    out = tmp_path / "run"
    asyncio.run(run_config(path, out, max_retries=0))
    resolved = yaml.safe_load((out / "config.resolved.yaml").read_text())
    assert resolved["max_retries_override"] == 0
    interrupt(out)
    with pytest.raises(ValueError, match=r"--max-retries 0, now not set"):
        asyncio.run(run_config(path, out, resume=True))
    with pytest.raises(ValueError, match=r"--max-retries 0, now 2"):
        asyncio.run(run_config(path, out, resume=True, max_retries=2))
    assert len(requests) == 1
    [attempt] = asyncio.run(run_config(path, out, resume=True, max_retries=0))
    assert attempt.retries == 0 and len(requests) == 2 and sleeps.delays == []


def test_resume_of_a_run_without_the_max_retries_flag(
    http_config: tuple[Path, list[int], Sleeps, list[int]], tmp_path: Path
) -> None:
    # Also the shape of runs recorded before the flag was persisted: absent means no override.
    path, statuses, sleeps, requests = http_config
    out = tmp_path / "run"
    asyncio.run(run_config(path, out))
    assert "max_retries_override" not in (out / "config.resolved.yaml").read_text()
    interrupt(out)
    with pytest.raises(ValueError, match=r"--max-retries not set, now 0"):
        asyncio.run(run_config(path, out, resume=True, max_retries=0))
    [attempt] = asyncio.run(run_config(path, out, resume=True))
    assert attempt.outcome == "pass"


class Clock:
    """Monotonic time in which backoff waits pass instantly; tests may advance ``offset``.

    The real clock still runs underneath, so the runner's request deadline, which asyncio
    enforces in real time, stays consistent with it."""

    def __init__(self) -> None:
        self.offset = 0.0
        self.delays: list[float] = []

    def __call__(self) -> float:
        return time.monotonic() + self.offset

    async def sleep(self, delay: float) -> None:
        self.delays.append(delay)
        self.offset += delay


def deadline_runner(
    clock: Clock,
    handler: Callable[[httpx.Request], Coroutine[None, None, httpx.Response]],
    **retry: Any,
) -> HTTPRunner:
    runner = HTTPRunner(
        {"model": "m", "base_url_env": "TEST_BASE", "api_key_env": "TEST_KEY", "timeout_s": 1},
        transport=httpx.MockTransport(handler),
        sleep=clock.sleep,
        clock=clock,
    )
    runner.retry_policy = RetryPolicy(jitter="none", multiplier=1, **retry)
    return runner


def test_timeout_covers_every_request_and_wait(
    task_path: Path, workdir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TEST_KEY", "fixture-key")
    monkeypatch.setenv("TEST_BASE", BASE)
    clock = Clock()
    requests: list[float] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(clock())
        clock.offset += 0.15  # a request that takes 0.15 s and fails
        return httpx.Response(503)

    runner = deadline_runner(clock, handler, max_retries=10, base_delay_s=0.2)
    start = clock()
    with pytest.raises(RunnerError) as caught:
        asyncio.run(runner.generate(load_task(task_path), workdir))
    elapsed = clock() - start
    # Requests end at 0.15, 0.5 and 0.85; a fourth 0.2 s wait would end past 1 s.
    assert caught.value.timed_out and str(caught.value) == "API request timed out"
    assert caught.value.retry_reasons == ("http_503",) * 2
    assert len(requests) == 3 and clock.delays == [0.2, 0.2]
    assert elapsed <= 1


def test_a_wait_that_would_cross_the_deadline_is_not_taken(
    task_path: Path, workdir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TEST_KEY", "fixture-key")
    monkeypatch.setenv("TEST_BASE", BASE)
    clock = Clock()

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"retry-after": "0.6"})

    runner = deadline_runner(clock, handler, max_retries=5)
    start = clock()
    with pytest.raises(RunnerError) as caught:
        asyncio.run(runner.generate(load_task(task_path), workdir))
    # One 0.6 s wait fits in the 1 s budget; the second would end at 1.2 s.
    assert caught.value.timed_out and caught.value.retry_reasons == ("http_429",)
    assert clock.delays == [0.6] and clock() - start < 1


def test_a_request_gets_only_the_remaining_budget(
    task_path: Path, workdir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TEST_KEY", "fixture-key")
    monkeypatch.setenv("TEST_BASE", BASE)
    clock = Clock()
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503)
        await asyncio.sleep(30)  # hangs; only the deadline ends it
        return httpx.Response(200, json=REPLY)  # pragma: no cover

    runner = deadline_runner(clock, handler, base_delay_s=0.9)
    start = clock()
    with pytest.raises(RunnerError) as caught:
        asyncio.run(runner.generate(load_task(task_path), workdir))
    elapsed = clock() - start
    # After a 0.9 s wait the second request has about 0.1 s left, not a fresh second.
    assert caught.value.timed_out and caught.value.retry_reasons == ("http_503",)
    assert 0.95 <= elapsed < 1.5 and calls == 2


def test_no_request_starts_after_the_deadline(
    task_path: Path, workdir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TEST_KEY", "fixture-key")
    monkeypatch.setenv("TEST_BASE", BASE)
    clock = Clock()
    calls = 0

    async def oversleep(delay: float) -> None:
        clock.offset += delay + 0.5  # an event loop can wake up late

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503)

    runner = deadline_runner(clock, handler, base_delay_s=0.6)
    runner.sleep = oversleep
    with pytest.raises(RunnerError) as caught:
        asyncio.run(runner.generate(load_task(task_path), workdir))
    assert caught.value.timed_out and caught.value.retry_reasons == ("http_503",)
    assert calls == 1
