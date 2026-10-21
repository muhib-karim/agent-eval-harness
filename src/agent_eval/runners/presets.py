"""Command templates for agent CLIs run headless by the ``cli`` runner.

Flags follow each tool's non-interactive mode as documented in October 2026. CLIs change
quickly, so every preset can be overridden piecewise (``executable``, ``extra_args``,
``timeout_s``, ``env_passthrough``) or replaced entirely with a plain ``command``.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any, Literal

PresetName = Literal["claude-code", "codex", "opencode"]

# Always forwarded so the agent can find its binary, its locale and a temp directory.
BASE_ENV = ("PATH", "HOME", "LANG", "LC_ALL", "TERM", "TMPDIR", "USER", "SYSTEMROOT")


@dataclass(frozen=True)
class Preset:
    executable: str
    args: tuple[str, ...]
    model_flag: str
    env: tuple[str, ...]
    timeout_s: float
    usage: Literal["claude-json"] | None = None


PRESETS: dict[str, Preset] = {
    # Print mode with JSON output; edits are auto-accepted and tools limited to file I/O.
    "claude-code": Preset(
        executable="claude",
        args=(
            "-p",
            "{prompt}",
            "--output-format",
            "json",
            "--permission-mode",
            "acceptEdits",
            "--allowedTools",
            "Read,Edit,Write",
        ),
        model_flag="--model",
        env=("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL"),
        timeout_s=600,
        usage="claude-json",
    ),
    # Non-interactive exec in a workspace-write sandbox rooted at the attempt's workdir.
    "codex": Preset(
        executable="codex",
        args=("exec", "--full-auto", "--skip-git-repo-check", "--cd", "{workdir}", "{prompt}"),
        model_flag="--model",
        env=("OPENAI_API_KEY", "OPENAI_BASE_URL", "CODEX_HOME"),
        timeout_s=600,
    ),
    "opencode": Preset(
        executable="opencode",
        args=("run", "{prompt}"),
        model_flag="--model",
        env=("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY", "OPENCODE_CONFIG"),
        timeout_s=600,
    ),
}


def parse_usage(kind: str | None, output: str) -> tuple[int | None, int | None, float | None]:
    """Tokens and cost the CLI itself reported; anything missing or malformed stays unknown."""
    if kind != "claude-json":
        return None, None, None
    try:
        data = json.loads(output.strip().splitlines()[-1])
    except (IndexError, ValueError):
        return None, None, None
    if not isinstance(data, dict):
        return None, None, None
    usage = data.get("usage")
    usage = usage if isinstance(usage, dict) else {}
    return (
        _count(usage.get("input_tokens")),
        _count(usage.get("output_tokens")),
        _usd(data.get("total_cost_usd")),
    )


def _count(value: Any) -> int | None:
    return value if type(value) is int and value >= 0 else None


def _usd(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if value >= 0 and math.isfinite(value) else None
