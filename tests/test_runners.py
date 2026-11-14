import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import httpx
import pytest

from agent_eval.runners.base import RunnerError, extract_code
from agent_eval.runners.http import HTTPRunner
from agent_eval.runners.local import CLIRunner, MockRunner
from agent_eval.specs import load_task

BASE = str(httpx.URL(scheme="https", host="endpoint.invalid", path="/v1"))


async def no_sleep(delay: float) -> None:
    return None


@pytest.mark.parametrize(
    "reply,expected",
    [
        ("x = 1", "x = 1\n"),
        ("Here it is:\n```python\nx = 1\n```\nDone.", "x = 1\n"),
        ("```json\n{}\n```\n```py\nx = 1\n```", "x = 1\n"),
        ("```\nx = 1\n```", "x = 1\n"),
        ("~~~Python3\nx = 1\n~~~", "x = 1\n"),
        ("```python\nx = 1", "x = 1\n"),
        ("```python\nx = 1\n```\n```python\ny = 2\n```", "x = 1\n\ny = 2\n"),
        ("```python title=solution.py\nx = 1\n```", "x = 1\n"),
        ("```{.python}\nx = 1\n```", "x = 1\n"),
        (
            "1. Code:\n\n   ```python\n   def f():\n       return 1\n   ```",
            "def f():\n    return 1\n",
        ),
    ],
)
def test_code_extraction(reply: str, expected: str) -> None:
    assert extract_code(reply) == expected


@pytest.mark.parametrize("reply", ["", "  ", "```json\n{}\n```", "```python\n \n```"])
def test_invalid_code(reply: str) -> None:
    with pytest.raises(RunnerError):
        extract_code(reply)


@pytest.mark.parametrize(
    "reply",
    [
        # An unlabeled fence holding a shell transcript rather than Python.
        "```\n$ pytest -q\n1 passed\n```",
        # A unified diff in a plain fence.
        "```\n--- a/solution.py\n+++ b/solution.py\n@@ -1 +1 @@\n"
        "-def answer(): return 0\n+def answer(): return 42\n```",
        # Python, then prose that escaped the fence (an endpoint cut the closing fence).
        "Here you go:\n```python\ndef answer():\n    return 42\nThat should do it.",
        # A traceback pasted in a plain fence: not source, despite the ``File "..."`` lines.
        '```\nTraceback (most recent call last):\n  File "solution.py", line 1\n'
        "NameError: answer\n```",
        # Indented prose block, common in explanations.
        "```\n    Run the tests with pytest.\n```",
    ],
)
def test_code_that_does_not_parse_is_an_extraction_failure(reply: str) -> None:
    """The harness must not write a diff, a transcript or prose to the entrypoint and
    record it as the model's solution: that is misleading evidence and a paid attempt
    whose failure cannot be told apart from a wrong answer."""
    with pytest.raises(RunnerError) as caught:
        extract_code(reply)
    # Same idiom as the other extraction failures: a short reason, raw reply attached.
    assert "parse" in str(caught.value).lower()
    assert caught.value.raw_output == reply


def test_a_null_byte_is_an_extraction_failure_on_every_supported_python() -> None:
    """``ast.parse`` rejects a null byte as ValueError on 3.11 and SyntaxError on 3.12+;
    both are extraction failures, so the 3.11 matrix entry cannot crash the attempt."""
    reply = "```python\nx = 1\x00\n```"
    with pytest.raises(RunnerError, match="parse") as caught:
        extract_code(reply)
    assert caught.value.raw_output == reply


def test_a_non_syntax_parser_error_is_also_an_extraction_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """3.11's ast.parse raises ValueError for some inputs, 3.12's SyntaxError. Pin the
    ValueError branch directly so the 3.11 matrix entry stays covered from any interpreter."""
    import ast

    def refuse(source: str) -> ast.AST:
        raise ValueError("source code string cannot contain null bytes")

    monkeypatch.setattr(ast, "parse", refuse)
    with pytest.raises(RunnerError, match="parse") as caught:
        extract_code("```python\nx = 1\n```")
    assert caught.value.raw_output == "```python\nx = 1\n```"


@pytest.mark.parametrize("anthropic", [False, True])
def test_http_success(
    anthropic: bool, task_path: Path, workdir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TEST_KEY", "secret-value")
    # A reserved invalid host; the transport intercepts every request.
    monkeypatch.setenv("TEST_BASE", BASE + "/")

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["model"] == "test-model"
        assert "answer()" in payload["messages"][0]["content"]
        assert "hidden" not in payload["messages"][0]["content"]
        assert payload["temperature"] == 0
        content = "```python\ndef answer():\n    return 42\n```"
        if anthropic:
            assert request.url.path == "/v1/messages"
            assert request.headers["x-api-key"] == "secret-value"
            assert request.headers["anthropic-version"] == "2023-06-01"
            body: dict[str, Any] = {
                "content": [{"type": "text", "text": content}],
                "usage": {"input_tokens": 10, "output_tokens": 20, "cost_usd": 0.01},
            }
        else:
            assert request.url.path == "/v1/chat/completions"
            assert request.headers["Authorization"] == "Bearer secret-value"
            body = {
                "choices": [{"message": {"content": content}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 20, "cost_usd": 0.01},
            }
        return httpx.Response(200, json=body)

    runner = HTTPRunner(
        {
            "model": "test-model",
            "base_url_env": "TEST_BASE",
            "api_key_env": "TEST_KEY",
            "temperature": 0,
        },
        anthropic=anthropic,
        transport=httpx.MockTransport(handler),
    )
    result = asyncio.run(runner.generate(load_task(task_path), workdir))
    assert result.input_tokens == 10 and result.output_tokens == 20
    assert result.cost_usd == 0.01
    assert (workdir / "solution.py").read_text() == "def answer():\n    return 42\n"


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"choices": []},
        {"choices": [{"message": {"content": None}}]},
        {"choices": [{"message": {"content": "pass"}}], "usage": {"prompt_tokens": -1}},
        {"choices": [{"message": {"content": "pass"}}], "usage": {"cost_usd": -1}},
        {"choices": [{"message": {"content": "pass"}}], "usage": {"cost_usd": "free"}},
    ],
)
def test_invalid_http_responses(
    body: dict[str, Any], task_path: Path, workdir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TEST_KEY", "secret-value")
    monkeypatch.setenv("TEST_BASE", BASE)
    runner = HTTPRunner(
        {"model": "test", "base_url_env": "TEST_BASE", "api_key_env": "TEST_KEY"},
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=body)),
    )
    with pytest.raises(RunnerError, match="invalid response"):
        asyncio.run(runner.generate(load_task(task_path), workdir))


@pytest.mark.parametrize("mode", ["missing", "status", "timeout", "missing_usage", "invalid_json"])
def test_http_error_and_unknown_usage(
    mode: str, task_path: Path, workdir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("TEST_KEY", raising=False)
    if mode != "missing":
        monkeypatch.setenv("TEST_KEY", "secret-value")
    monkeypatch.setenv("TEST_BASE", BASE)

    def handler(request: httpx.Request) -> httpx.Response:
        if mode == "timeout":
            raise httpx.ReadTimeout("secret-value", request=request)
        if mode == "status":
            return httpx.Response(429, text="secret-value")
        if mode == "invalid_json":
            return httpx.Response(200, text="not json")
        return httpx.Response(200, json={"choices": [{"message": {"content": "pass"}}]})

    runner = HTTPRunner(
        {"model": "test", "base_url_env": "TEST_BASE", "api_key_env": "TEST_KEY"},
        transport=httpx.MockTransport(handler),
        sleep=no_sleep,
    )
    if mode == "missing_usage":
        result = asyncio.run(runner.generate(load_task(task_path), workdir))
        assert result.input_tokens is result.output_tokens is result.cost_usd is None
    else:
        with pytest.raises(RunnerError) as caught:
            asyncio.run(runner.generate(load_task(task_path), workdir))
        assert "secret-value" not in str(caught.value)
        assert caught.value.timed_out == (mode == "timeout")
        if mode == "status":
            assert str(caught.value) == "API request failed with HTTP 429"
            assert caught.value.retry_reasons == ("http_429",) * 3
        if mode == "timeout":
            assert caught.value.retry_reasons == ("ReadTimeout",) * 3


def test_unparseable_reply_is_recorded_as_an_extraction_failure(
    task_path: Path, workdir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A transcript in a plain fence must not reach the entrypoint. The attempt is an
    ``error`` with the extraction reason, no solution.py artifact, and the raw reply kept
    in model-output.txt so the evidence shows what the model actually said."""
    monkeypatch.setenv("TEST_KEY", "secret-value")
    monkeypatch.setenv("TEST_BASE", BASE)
    reply = "```\n$ pytest -q\n1 passed\n```"
    runner = HTTPRunner(
        {"model": "test", "base_url_env": "TEST_BASE", "api_key_env": "TEST_KEY"},
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"choices": [{"message": {"content": reply}}]})
        ),
        sleep=no_sleep,
    )
    with pytest.raises(RunnerError, match="parse") as caught:
        asyncio.run(runner.generate(load_task(task_path), workdir))
    assert caught.value.generation.raw_output == reply
    assert not (workdir / "solution.py").exists()


def test_http_transport_error_names_the_failure(
    task_path: Path, workdir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TEST_KEY", "secret-value")
    monkeypatch.setenv("TEST_BASE", BASE)

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("secret-value", request=request)

    runner = HTTPRunner(
        {"model": "test", "base_url_env": "TEST_BASE", "api_key_env": "TEST_KEY"},
        transport=httpx.MockTransport(handler),
        sleep=no_sleep,
    )
    with pytest.raises(RunnerError) as caught:
        asyncio.run(runner.generate(load_task(task_path), workdir))
    assert str(caught.value) == "API request failed: ConnectError"
    assert caught.value.retry_reasons == ("ConnectError",) * 3


def test_cli_writes_files_without_hidden_tests(task_path: Path, workdir: Path) -> None:
    script = task_path.parent / "agent.py"
    script.write_text(
        "from pathlib import Path\nimport sys\n"
        "assert not list(Path.cwd().glob('*hidden*'))\n"
        "assert 'answer()' in Path(sys.argv[1]).read_text()\n"
        "Path(sys.argv[2]).write_text('def answer(): return 42')\nprint('generated')\n"
    )
    runner = CLIRunner({"command": [sys.executable, str(script), "{prompt_file}", "{entrypoint}"]})
    result = asyncio.run(runner.generate(load_task(task_path), workdir))
    assert result.raw_output == "generated\n"
    assert (workdir / "solution.py").is_file()


@pytest.mark.parametrize("timeout", [False, True])
def test_cli_failure(timeout: bool, task_path: Path, workdir: Path) -> None:
    code = (
        "import time; print('partial',flush=True); time.sleep(20)"
        if timeout
        else "raise SystemExit(7)"
    )
    runner = CLIRunner({"command": [sys.executable, "-c", code], "timeout_s": 0.2})
    with pytest.raises(RunnerError) as caught:
        asyncio.run(runner.generate(load_task(task_path), workdir))
    assert caught.value.timed_out == timeout
    if timeout:
        assert "partial" in caught.value.raw_output


def test_cli_missing_command_is_a_runner_error(task_path: Path, workdir: Path) -> None:
    runner = CLIRunner({"command": [str(workdir / "no-such-agent")]})
    with pytest.raises(RunnerError, match="cannot start agent command: FileNotFoundError"):
        asyncio.run(runner.generate(load_task(task_path), workdir))


def test_mock_custom_fixture(task_path: Path, workdir: Path) -> None:
    (task_path.parent / "custom.py").write_text("value = 123\n")
    runner = MockRunner({"fixtures": {"answer": "custom.py"}}, task_path=task_path)
    result = asyncio.run(runner.generate(load_task(task_path), workdir))
    assert result.raw_output == "value = 123\n"


@pytest.mark.parametrize("token_param", ["max_tokens", "max_completion_tokens"])
def test_http_token_param(
    token_param: str, task_path: Path, workdir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TEST_KEY", "secret-value")
    monkeypatch.setenv("TEST_BASE", BASE)
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        body = {"choices": [{"message": {"content": "def answer():\n    return 42\n"}}]}
        return httpx.Response(200, json=body)

    runner = HTTPRunner(
        {
            "model": "test-model",
            "base_url_env": "TEST_BASE",
            "api_key_env": "TEST_KEY",
            "max_tokens": 321,
            "token_param": token_param,
        },
        transport=httpx.MockTransport(handler),
    )
    asyncio.run(runner.generate(load_task(task_path), workdir))
    assert seen[token_param] == 321
    other = {"max_tokens", "max_completion_tokens"} - {token_param}
    assert not other & seen.keys()
