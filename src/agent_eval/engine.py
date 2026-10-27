"""Async orchestration and durable, credential-redacted run artifacts."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import platform
import shutil
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from agent_eval import __version__
from agent_eval.grader import Grade, grade
from agent_eval.isolation import IsolationMode, select_isolation
from agent_eval.report import render_report
from agent_eval.results import Attempt, summarize
from agent_eval.retry import resolve_policy
from agent_eval.runners import create_runner
from agent_eval.runners.base import Generation, Runner, RunnerError
from agent_eval.runners.http import HTTPRunner
from agent_eval.runners.local import CLIOptions, CLIRunner, MockOptions
from agent_eval.specs import TaskSpec, discover_tasks, load_config, load_task, task_file


async def validate_task(path: Path, reference: Path | None = None) -> Grade:
    """Grade a reference solution: the task's own ``reference`` file or an external one."""
    task = load_task(path, require_reference=reference is None)
    source = task_file(path, task.reference) if reference is None else reference
    with tempfile.TemporaryDirectory(prefix="agent-eval-validate-") as directory:
        workdir = Path(directory)
        (workdir / task.entrypoint).write_bytes(source.read_bytes())
        return await grade(task, path, workdir)


def _resolve_options(runner: str, options: dict[str, Any], base: Path) -> dict[str, Any]:
    """Make the mock runner's ``reference_dir`` relative to the config, not the CWD."""
    reference_dir = options.get("reference_dir")
    if runner == "mock" and isinstance(reference_dir, str):
        return {**options, "reference_dir": str((base / reference_dir).resolve())}
    return options


def recover_attempts(path: Path) -> list[Attempt]:
    """Recorded attempts of an interrupted run; drops only a half-written final line."""
    data = path.read_bytes()
    lines = data.split(b"\n")
    attempts: list[Attempt] = []
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            attempts.append(Attempt.model_validate_json(line))
        except ValueError:
            if index == len(lines) - 1:
                # The process died mid-write; this attempt will run again.
                path.write_bytes(data[: len(data) - len(line)])
                break
            raise ValueError(f"cannot resume: invalid attempt on line {index + 1}") from None
    identities = {(row.model, row.task_id, row.repeat) for row in attempts}
    if len(identities) != len(attempts) or len({row.attempt_id for row in attempts}) != len(
        attempts
    ):
        raise ValueError("cannot resume: duplicate attempts in results.jsonl")
    return attempts


async def run_config(
    config_path: Path,
    out: Path,
    *,
    resume: bool = False,
    isolation: IsolationMode | None = None,
    max_retries: int | None = None,
) -> list[Attempt]:
    """Run every model x task x repeat. With ``resume``, fill in only the attempts that an
    interrupted run in ``out`` never recorded; recorded attempts, errors included, are kept.
    ``isolation`` overrides the config's ``isolation.mode`` and ``max_retries`` every HTTP
    model's ``retry.max_retries``."""
    config_path = config_path.resolve()
    config = load_config(config_path)
    tasks = discover_tasks(config.tasks, config_path.parent)
    # Validate every runner before creating a run directory or starting any generation.
    jobs: list[tuple[str, str, Path, TaskSpec, int, Runner]] = []
    retry = resolve_policy(config.retry, max_retries=max_retries)
    for model in config.models:
        options = _resolve_options(model.runner, model.options, config_path.parent)
        for task_path, task in tasks:
            for repeat in range(1, config.repeats + 1):
                runner = create_runner(model.runner, options, task_path=task_path)
                # CLI agents may already have changed the workdir, so only HTTP calls are retried.
                if isinstance(runner, HTTPRunner):
                    runner.retry_policy = resolve_policy(
                        retry, runner.options.retry, max_retries=max_retries
                    )
                jobs.append((model.name, model.runner, task_path, task, repeat, runner))
    isolation_options = config.isolation
    if isolation is not None:
        isolation_options = isolation_options.model_copy(update={"mode": isolation})
    sandbox, isolation_record = await select_isolation(isolation_options)
    if isolation_record.warning:
        print(f"agent-eval: warning: {isolation_record.warning}", file=sys.stderr)
    for job in jobs:
        if isinstance(job[5], CLIRunner):
            job[5].sandbox = sandbox
    secrets = [
        os.environ[value]
        for model in config.models
        for name, value in model.options.items()
        if name == "api_key_env" and isinstance(value, str) and os.environ.get(value)
    ]
    # Credentials forwarded to agent CLIs; short values are skipped to avoid redacting noise.
    for model in config.models:
        if model.runner == "cli":
            for name in CLIOptions.model_validate(model.options).passthrough_names():
                if len(os.environ.get(name, "")) >= 8:
                    secrets.append(os.environ[name])

    def redact(value: str) -> str:
        for secret in sorted(secrets, key=len, reverse=True):
            value = value.replace(secret, "[REDACTED]")
        return value

    out = out.resolve()
    resolved = config.model_dump(mode="json")
    resolved["tasks"] = [str(path) for path, _ in tasks]
    # The effective mode, after --isolation. A local run of a config without an isolation
    # block records none, like runs from before isolation existed, which stay resumable.
    resolved["isolation"] = isolation_options.model_dump(mode="json")
    if "isolation" not in config.model_fields_set and isolation_options.mode == "local":
        del resolved["isolation"]
    if "retry" not in config.model_fields_set:
        del resolved["retry"]
    config_text = redact(yaml.safe_dump(resolved, sort_keys=False))
    hashes: dict[str, dict[str, str]] = {}
    for path, task in tasks:
        sources = [path, *(task_file(path, name) for name in task.hidden_tests)]
        if task.starter is not None:
            sources.append(task_file(path, task.starter))
        if (path.parent / task.reference).is_file():
            sources.append(task_file(path, task.reference))
        for model in config.models:
            if model.runner == "mock":
                mock = MockOptions.model_validate(
                    _resolve_options(model.runner, model.options, config_path.parent)
                )
                reference = mock.reference_file(task.id)
                if mock.variant == "reference" and task.id in mock.fixtures:
                    sources.append(task_file(path, mock.fixtures[task.id]))
                elif mock.variant == "reference" and reference and reference.is_file():
                    sources.append(reference)
        hashes[task.id] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    metadata = {
        "schema_version": "1.0",
        "harness_version": __version__,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "started_at": datetime.now(UTC).isoformat(),
        "task_hashes": hashes,
        "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
    }
    done: list[Attempt] = []
    if resume and out.exists():
        if not (out / "results.jsonl").is_file():
            raise ValueError(f"cannot resume: no results.jsonl in {out}")
        previous_text = (out / "config.resolved.yaml").read_text(encoding="utf-8")
        # Runs recorded without an isolation entry ran locally.
        recorded_isolation = yaml.safe_load(previous_text).get("isolation") or {}
        previous_mode = recorded_isolation.get("mode", "local")
        if previous_mode != isolation_options.mode:
            raise ValueError(
                "cannot resume: the config differs from the interrupted run "
                f"(isolation {previous_mode}, now {isolation_options.mode})"
            )
        if previous_text != config_text:
            raise ValueError("cannot resume: the config differs from the interrupted run")
        previous = json.loads((out / "metadata.json").read_text(encoding="utf-8"))
        if previous.get("task_hashes") != json.loads(redact(json.dumps(hashes))):
            raise ValueError("cannot resume: task files changed since the interrupted run")
        done = recover_attempts(out / "results.jsonl")
        previous.setdefault("resumed_at", []).append(metadata["started_at"])
        metadata = previous
    else:
        out.mkdir(parents=True, exist_ok=False)
        (out / "config.resolved.yaml").write_text(config_text, encoding="utf-8")
    (out / "metadata.json").write_text(
        redact(json.dumps(metadata, indent=2)) + "\n", encoding="utf-8"
    )
    recorded = {(row.model, row.task_id, row.repeat) for row in done}
    semaphore = asyncio.Semaphore(config.concurrency)
    attempts: list[Attempt] = list(done)
    with (out / "results.jsonl").open("a" if done else "w", encoding="utf-8") as stream:

        async def execute(index: int, job: tuple[str, str, Path, TaskSpec, int, Runner]) -> None:
            async with semaphore:
                model_name, runner_name, task_path, task, repeat, runner = job
                attempt_id = f"attempt-{index:06d}"
                artifact_dir = out / "attempts" / attempt_id
                # Leftovers of an attempt that was interrupted before it was recorded.
                shutil.rmtree(artifact_dir, ignore_errors=True)
                artifact_dir.mkdir(parents=True)
                start = time.perf_counter()
                grading_time = 0.0
                generated = Generation("")
                graded = Grade("error")
                error: str | None = None
                with tempfile.TemporaryDirectory(prefix="agent-eval-") as directory:
                    workdir = Path(directory)
                    try:
                        if task.starter is not None:
                            shutil.copyfile(
                                task_file(task_path, task.starter), workdir / task.entrypoint
                            )
                        generated = await runner.generate(task, workdir)
                        generation_end = time.perf_counter()
                        graded = await grade(task, task_path, workdir, sandbox)
                        grading_time = time.perf_counter() - generation_end
                    except RunnerError as exc:
                        generation_end = time.perf_counter()
                        generated = exc.generation
                        graded = Grade("timeout" if exc.timed_out else "error")
                        error = str(exc)
                    except Exception as exc:
                        generation_end = time.perf_counter()
                        error = f"attempt failed: {type(exc).__name__}"
                    entrypoint = workdir / task.entrypoint
                    if entrypoint.is_file() and not entrypoint.is_symlink():
                        (artifact_dir / "solution.py").write_text(
                            redact(entrypoint.read_text(encoding="utf-8", errors="replace")),
                            encoding="utf-8",
                        )
                (artifact_dir / "model-output.txt").write_text(
                    redact(generated.raw_output), encoding="utf-8"
                )
                (artifact_dir / "test.log").write_text(redact(graded.log), encoding="utf-8")
                attempt = Attempt(
                    attempt_id=attempt_id,
                    model=redact(model_name),
                    runner=runner_name,
                    task_id=task.id,
                    repeat=repeat,
                    outcome=graded.outcome,
                    tests_passed=graded.passed,
                    tests_total=graded.total,
                    wall_time_s=time.perf_counter() - start,
                    generation_time_s=generation_end - start,
                    grading_time_s=grading_time,
                    input_tokens=generated.input_tokens,
                    output_tokens=generated.output_tokens,
                    cost_usd=generated.cost_usd,
                    error=redact(error) if error else None,
                    artifacts=str(artifact_dir.relative_to(out)),
                    category=task.category,
                    isolation=isolation_record,
                    retries=len(generated.retry_reasons),
                    retry_reasons=list(generated.retry_reasons),
                )
                stream.write(attempt.model_dump_json() + "\n")
                stream.flush()
                attempts.append(attempt)

        # Structured concurrency ensures cleanup completes before the result stream closes.
        async with asyncio.TaskGroup() as group:
            for index, job in enumerate(jobs, 1):
                if (redact(job[0]), job[3].id, job[4]) not in recorded:
                    group.create_task(execute(index, job))
    attempts.sort(key=lambda row: row.attempt_id)
    summary = summarize(attempts)
    (out / "summary.json").write_text(render_report(summary, "json"), encoding="utf-8")
    (out / "report.html").write_text(render_report(summary, "html"), encoding="utf-8")
    return attempts
