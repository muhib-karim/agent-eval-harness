from __future__ import annotations

import html
from importlib.resources import files
from typing import Literal

from jinja2 import Environment, StrictUndefined, select_autoescape

from agent_eval.results import Summary, summary_json

ReportFormat = Literal["md", "html", "json"]


def _md(value: str) -> str:
    return html.escape(value).replace("|", "&#124;").replace("\n", " ").replace("\r", " ")


def _count(value: int | None) -> str:
    return "unknown" if value is None else str(value)


def format_usd(value: float | None) -> str:
    """Hide float summation noise such as 0.30000000000000004 without dropping small costs."""
    if value is None:
        return "unknown"
    return f"{value:.6f}".rstrip("0").rstrip(".")


def render_report(summary: Summary, fmt: ReportFormat) -> str:
    if fmt == "json":
        return summary_json(summary)
    if fmt == "md":
        boot = summary.bootstrap
        level = f"{boot.confidence:.0%}"
        lines = [
            "# Coding task comparison",
            "",
            f"{summary.attempts} attempts. Pass rates are task-macro-averaged. "
            "Missing usage is unknown.",
            "",
            f"{level} CI: {boot.method}, {boot.resamples} resamples, seed {boot.seed}.",
            "",
            f"| Model | Pass@1 | {level} CI | Pass@k | Mean (s) | Median (s) | "
            "Input / output tokens | Cost (USD) |",
            "| --- | ---: | ---: | --- | ---: | ---: | --- | --- |",
        ]
        for model in summary.models:
            estimates = ", ".join(f"{k}: {v:.1%}" for k, v in model.pass_at_k.items())
            low, high = model.pass_at_1_ci
            lines.append(
                f"| {_md(model.model)} | {model.pass_at_1:.1%} | {low:.1%}–{high:.1%} | "
                f"{estimates} | "
                f"{model.mean_wall_time_s:.3f} | {model.median_wall_time_s:.3f} | "
                f"{_count(model.input_tokens)} / {_count(model.output_tokens)} | "
                f"{format_usd(model.cost_usd)} |"
            )
        lines.extend(["", "## Per-task passes / attempts", ""])
        lines.append("| Task | " + " | ".join(_md(m.model) for m in summary.models) + " |")
        lines.append("| --- | " + " | ".join("---:" for _ in summary.models) + " |")
        for task in summary.task_ids:
            cells = []
            for model in summary.models:
                score = next((s for s in model.tasks if s.task_id == task), None)
                cells.append(f"{score.passed}/{score.attempts}" if score else "—")
            lines.append(f"| {_md(task)} | " + " | ".join(cells) + " |")
        categories = sorted(set(summary.task_categories.values()))
        lines.extend(["", "## Pass@1 by category", ""])
        lines.append(
            "| Category | Tasks | " + " | ".join(_md(m.model) for m in summary.models) + " |"
        )
        lines.append("| --- | ---: | " + " | ".join("---:" for _ in summary.models) + " |")
        for category in categories:
            count = sum(c == category for c in summary.task_categories.values())
            cells = []
            for model in summary.models:
                found = next((c for c in model.categories if c.category == category), None)
                cells.append(f"{found.pass_at_1:.1%}" if found else "—")
            lines.append(f"| {_md(category)} | {count} | " + " | ".join(cells) + " |")
        if summary.comparisons:
            lines.extend(["", "## Paired comparisons where intervals overlap", ""])
            for item in summary.comparisons:
                lines.append(
                    f"- {_md(item.model_a)} − {_md(item.model_b)}: {item.diff:+.1%} "
                    f"(paired {level} CI {item.ci_low:+.1%} to {item.ci_high:+.1%}). "
                    f"{_md(item.note)}"
                )
        lines.extend(
            [
                "",
                "Reported totals may be partial. Usage coverage (attempts with input/output/cost):",
                "",
            ]
        )
        for model in summary.models:
            lines.append(
                f"- {_md(model.model)}: {model.input_tokens_reported}/"
                f"{model.output_tokens_reported}/{model.cost_reported} of {model.attempts}."
            )
        return "\n".join(lines) + "\n"
    if fmt != "html":
        raise ValueError(f"unsupported report format: {fmt}")
    environment = Environment(autoescape=select_autoescape(default=True), undefined=StrictUndefined)
    environment.filters["usd"] = format_usd
    environment.filters["pct"] = format_pct
    environment.filters["heat"] = heat_level
    environment.filters["count"] = _count
    template = files("agent_eval").joinpath("templates/report.html").read_text(encoding="utf-8")
    max_time = max(t for m in summary.models for t in m.wall_times_s) or 1
    categories = sorted(set(summary.task_categories.values()))
    return environment.from_string(template).render(
        summary=summary,
        max_time=max_time,
        categories=categories,
        category_sizes={
            name: sum(c == name for c in summary.task_categories.values()) for name in categories
        },
        level=f"{summary.bootstrap.confidence:.0%}",
    )


def format_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def heat_level(value: float) -> int:
    """Five equal-width pass-rate bands, 0 (0-20%) to 4 (80-100%), for the heatmap colours."""
    return min(4, max(0, int(value * 5)))
