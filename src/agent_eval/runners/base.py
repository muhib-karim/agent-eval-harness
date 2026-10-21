"""Public extension contract. Runners generate files; graders own the tests."""

from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from agent_eval.specs import TaskSpec


@dataclass(frozen=True)
class Generation:
    raw_output: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


class RunnerError(Exception):
    """A sanitized generation failure, optionally including partial output."""

    def __init__(
        self,
        message: str,
        *,
        raw_output: str = "",
        timed_out: bool = False,
        generation: Generation | None = None,
    ) -> None:
        super().__init__(message)
        self.generation = generation or Generation(raw_output)
        self.raw_output = self.generation.raw_output
        self.timed_out = timed_out


class Runner(Protocol):
    async def generate(self, task: TaskSpec, workdir: Path) -> Generation:
        """Write ``task.entrypoint`` into ``workdir`` and return the raw output and usage."""


class RunnerFactory(Protocol):
    def __call__(self, options: dict[str, Any], *, task_path: Path) -> Runner:
        """Build a runner from a model's ``options`` for the task at ``task_path``."""


def extract_code(reply: str) -> str:
    """Prefer Python fences, then unlabeled fences; preserve unfenced source."""
    blocks = re.findall(r"^[ \t]*(`{3,}|~{3,})([^\n]*)\n(.*?)^\s*\1\s*$", reply, re.M | re.S)
    for labels in ({"python", "py", "python3"}, {""}):
        # The language is the info string's first word, e.g. "python title=solution.py".
        selected = [body for _, info, body in blocks if _language(info) in labels]
        if selected:
            if not any(body.strip() for body in selected):
                raise RunnerError("model returned empty code", raw_output=reply)
            # Fences nested in Markdown lists are indented along with their contents.
            return "\n\n".join(textwrap.dedent(body).strip("\n") for body in selected) + "\n"
    if blocks:
        raise RunnerError("reply contains no Python or unlabeled code block", raw_output=reply)
    # Some endpoints truncate the final closing fence.
    opening = re.search(r"^\s*(?:`{3,}|~{3,})(?:python3?|py)?\s*\n", reply, re.M)
    code = reply[opening.end() :] if opening else reply
    if not code.strip():
        raise RunnerError("model returned empty code", raw_output=reply)
    return code.strip("\n") + "\n"


def _language(info: str) -> str:
    words = info.strip().strip("{}").split()
    return words[0].lstrip(".").lower() if words else ""


def generation_prompt(task: TaskSpec, starter_source: str | None = None) -> str:
    if starter_source is None:
        return (
            f"Implement this Python task in {task.entrypoint}. "
            "Use only the Python standard library.\n"
            "Return the complete source code in a single Python code block.\n\n" + task.prompt
        )
    return (
        f"Fix the bug described below in {task.entrypoint}. Use only the Python standard library.\n"
        "Return the complete fixed module in a single Python code block.\n\n"
        f"{task.prompt}\n\nCurrent {task.entrypoint}:\n\n```python\n{starter_source}```\n"
    )


def starter_source(task: TaskSpec, workdir: Path) -> str | None:
    """The bug-fix starter the engine placed at the entrypoint, if the task has one."""
    if task.starter is None:
        return None
    path = workdir / task.entrypoint
    return path.read_text(encoding="utf-8") if path.is_file() else None
