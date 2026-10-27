from __future__ import annotations

import contextlib
import os
import shlex
import string
import tempfile
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import Field, field_validator, model_validator

from agent_eval.isolation import Sandbox
from agent_eval.process import run_process
from agent_eval.runners.base import Generation, RunnerError
from agent_eval.runners.presets import BASE_ENV, PRESETS, PresetName, parse_usage
from agent_eval.specs import PositiveSeconds, StrictModel, TaskSpec, task_file

PLACEHOLDERS = {"prompt", "prompt_file", "workdir", "entrypoint"}
ENV_NAME = r"^[A-Za-z_][A-Za-z0-9_]*$"


class CLIOptions(StrictModel):
    """Either a ``preset`` (claude-code, codex, opencode) or an explicit ``command``."""

    preset: PresetName | None = None
    command: list[str] | None = None
    # Preset overrides: binary path, model id, and arguments appended to the template.
    executable: str | None = Field(default=None, min_length=1)
    model: str | None = Field(default=None, min_length=1)
    extra_args: list[str] = Field(default_factory=list)
    timeout_s: PositiveSeconds | None = None
    # Extra variable names forwarded to the agent; everything else is withheld.
    env_passthrough: list[Annotated[str, Field(pattern=ENV_NAME)]] = Field(default_factory=list)
    # Give the agent an empty HOME/XDG/TMPDIR so it cannot read the host's config or history.
    isolate_home: bool = False

    @field_validator("command", mode="before")
    @classmethod
    def split_command(cls, value: Any) -> Any:
        return shlex.split(value) if isinstance(value, str) else value

    @field_validator("command", "extra_args")
    @classmethod
    def valid_placeholders(cls, parts: list[str] | None) -> list[str] | None:
        for part in parts or []:
            for _, name, fmt, conversion in string.Formatter().parse(part):
                if name is not None and (name not in PLACEHOLDERS or fmt or conversion):
                    raise ValueError("unsupported command placeholder")
        return parts

    @model_validator(mode="after")
    def preset_or_command(self) -> CLIOptions:
        if (self.preset is None) == (self.command is None):
            raise ValueError("set exactly one of preset or command")
        if self.command is not None:
            if not self.command or not self.command[0]:
                raise ValueError("command cannot be empty")
            if self.executable or self.model or self.extra_args:
                raise ValueError("executable, model and extra_args apply only to presets")
        return self

    def template(self) -> tuple[list[str], list[str]]:
        """Arguments to format with placeholders, then literal model arguments."""
        if self.command is not None:
            return list(self.command), []
        preset = PRESETS[self.preset or ""]
        model = [preset.model_flag, self.model] if self.model else []
        return [self.executable or preset.executable, *preset.args, *self.extra_args], model

    def timeout(self) -> float:
        if self.timeout_s is not None:
            return self.timeout_s
        return PRESETS[self.preset].timeout_s if self.preset else 120

    def passthrough_names(self) -> list[str]:
        """Names forwarded beyond the base environment, e.g. credentials."""
        preset = PRESETS[self.preset].env if self.preset else ()
        return list(dict.fromkeys([*preset, *self.env_passthrough]))

    def environment(self, home: Path | None) -> dict[str, str]:
        names = [*BASE_ENV, *self.passthrough_names()]
        env = {name: os.environ[name] for name in names if name in os.environ}
        if home is not None:
            for name in ("HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME", "TMPDIR"):
                env[name] = str(home)
        return env


class CLIRunner:
    def __init__(self, options: dict[str, Any]) -> None:
        self.options = CLIOptions.model_validate(options)
        # Set by the engine for docker isolation; the command then runs in the image.
        self.sandbox: Sandbox | None = None

    async def generate(self, task: TaskSpec, workdir: Path) -> Generation:
        prompt_file = workdir / "_agent_prompt.txt"
        instruction = (
            f"Fix the bug described below in {task.entrypoint}, which is in this directory."
            if task.starter
            else f"Write your Python implementation to {task.entrypoint}."
        )
        prompt = f"{instruction}\n\n{task.prompt}"
        prompt_file.write_text(prompt, encoding="utf-8")
        values = {
            "prompt": prompt,
            "prompt_file": str(prompt_file),
            "workdir": str(workdir),
            "entrypoint": task.entrypoint,
        }
        template, literal = self.options.template()
        args = [part.format(**values) for part in template] + literal
        with contextlib.ExitStack() as stack:
            home = None
            # A container's HOME is already a private tmpfs.
            if self.options.isolate_home and self.sandbox is None:
                home = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="agent-home-")))
            env = self.options.environment(home)
            try:
                if self.sandbox is None:
                    result = await run_process(args, workdir, self.options.timeout(), env)
                else:
                    result = await self.sandbox.run(args, workdir, self.options.timeout(), env)
            except OSError as exc:
                raise RunnerError(f"cannot start agent command: {type(exc).__name__}") from exc
        if result.timed_out:
            raise RunnerError("agent timed out", raw_output=result.output, timed_out=True)
        usage = parse_usage(
            PRESETS[self.options.preset].usage if self.options.preset else None, result.output
        )
        generation = Generation(result.output, *usage)
        if result.returncode:
            raise RunnerError(f"agent exited with code {result.returncode}", generation=generation)
        return generation


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
