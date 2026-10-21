from __future__ import annotations

import shlex
import string
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, field_validator

from agent_eval.process import run_process
from agent_eval.runners.base import Generation, RunnerError
from agent_eval.specs import PositiveSeconds, StrictModel, TaskSpec, task_file


class CLIOptions(StrictModel):
    command: list[str]
    timeout_s: PositiveSeconds = 120

    @field_validator("command", mode="before")
    @classmethod
    def split_command(cls, value: Any) -> Any:
        return shlex.split(value) if isinstance(value, str) else value

    @field_validator("command")
    @classmethod
    def valid_command(cls, parts: list[str]) -> list[str]:
        if not parts or not parts[0]:
            raise ValueError("command cannot be empty")
        for part in parts:
            for _, name, fmt, conversion in string.Formatter().parse(part):
                if name is not None and (
                    name not in {"prompt_file", "workdir", "entrypoint"} or fmt or conversion
                ):
                    raise ValueError("unsupported command placeholder")
        return parts


class CLIRunner:
    def __init__(self, options: dict[str, Any]) -> None:
        self.options = CLIOptions.model_validate(options)

    async def generate(self, task: TaskSpec, workdir: Path) -> Generation:
        prompt_file = workdir / "_agent_prompt.txt"
        instruction = (
            f"Fix the bug described below in {task.entrypoint}, which is in this directory."
            if task.starter
            else f"Write your Python implementation to {task.entrypoint}."
        )
        prompt_file.write_text(f"{instruction}\n\n{task.prompt}", encoding="utf-8")
        args = [
            part.format(
                prompt_file=str(prompt_file), workdir=str(workdir), entrypoint=task.entrypoint
            )
            for part in self.options.command
        ]
        try:
            result = await run_process(args, workdir, self.options.timeout_s)
        except OSError as exc:
            raise RunnerError(f"cannot start agent command: {type(exc).__name__}") from exc
        if result.timed_out:
            raise RunnerError("agent timed out", raw_output=result.output, timed_out=True)
        if result.returncode:
            raise RunnerError(
                f"agent exited with code {result.returncode}", raw_output=result.output
            )
        return Generation(result.output)


class MockOptions(StrictModel):
    variant: Literal["reference", "wrong"] = "reference"
    fixtures: dict[str, str] = Field(default_factory=dict)
    # Directory of ``<task_id>.py`` solutions kept outside the task directories.
    # The engine resolves a relative path against the run config's directory.
    reference_dir: str | None = None

    def reference_file(self, task_id: str) -> Path | None:
        if self.reference_dir is None:
            return None
        return Path(self.reference_dir) / f"{task_id}.py"


class MockRunner:
    def __init__(self, options: dict[str, Any], *, task_path: Path) -> None:
        self.options = MockOptions.model_validate(options)
        self.task_path = task_path

    async def generate(self, task: TaskSpec, workdir: Path) -> Generation:
        if self.options.variant == "wrong":
            code = (
                "# Deliberately wrong offline fixture.\n"
                "def __getattr__(name):\n    return lambda *args, **kwargs: None\n"
            )
        elif task.id in self.options.fixtures:
            code = task_file(self.task_path, self.options.fixtures[task.id]).read_text("utf-8")
        elif (reference := self.options.reference_file(task.id)) is not None:
            if not reference.is_file():
                raise RunnerError(f"no reference solution for task {task.id}")
            code = reference.read_text(encoding="utf-8")
        else:
            code = task_file(self.task_path, task.reference).read_text(encoding="utf-8")
        (workdir / task.entrypoint).write_text(code, encoding="utf-8")
        return Generation(code)
