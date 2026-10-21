"""Snapshot-style checks of the self-contained HTML report: structure, escaping, usage, sorting."""

import re
from html.parser import HTMLParser

import pytest

from agent_eval.report import format_pct, heat_level, render_report
from agent_eval.results import Attempt, Summary, summarize

VOID = {"meta", "br", "img", "input", "link", "hr", "source", "wbr"}
HOSTILE = '<img src=x onerror="alert(1)">&"model\''


def attempt(model: str, task: str, repeat: int, passed: bool, **extra: object) -> Attempt:
    fields: dict[str, object] = {
        "attempt_id": f"{model}-{task}-{repeat}",
        "model": model,
        "runner": "mock",
        "task_id": task,
        "repeat": repeat,
        "outcome": "pass" if passed else "fail",
        "wall_time_s": 1.0 + repeat,
        "generation_time_s": 1.0,
        "grading_time_s": 0.5,
        "artifacts": "attempts/x",
        "category": "parsing" if task.startswith("p") else "algorithms",
    }
    fields.update(extra)
    return Attempt.model_validate(fields)


def summary() -> Summary:
    rows = []
    for task in ("p1", "p2", "a1"):
        for repeat in (1, 2):
            # "reported" has full usage, "partial" has some, HOSTILE has none.
            rows.append(
                attempt(
                    "reported",
                    task,
                    repeat,
                    True,
                    input_tokens=10,
                    output_tokens=20,
                    cost_usd=0.5,
                )
            )
            rows.append(
                attempt(
                    "partial",
                    task,
                    repeat,
                    repeat == 1,
                    input_tokens=5 if repeat == 1 else None,
                    output_tokens=7,
                )
            )
            rows.append(attempt(HOSTILE, task, repeat, task == "a1"))
    return summarize(rows, (1, 2), seed=1, resamples=200)


class Outline(HTMLParser):
    """Records the element tree shape and fails on unbalanced tags."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.starts: list[tuple[str, dict[str, str | None]]] = []
        self.headings: list[tuple[str, str]] = []
        self.captions: list[str] = []
        self._text: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.starts.append((tag, dict(attrs)))
        if tag in {"h1", "h2", "h3", "caption"}:
            self._text = []
        if tag not in VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.starts.append((tag, dict(attrs)))

    def handle_endtag(self, tag: str) -> None:
        assert self.stack and self.stack[-1] == tag, f"unbalanced </{tag}> in {self.stack[-3:]}"
        self.stack.pop()
        if tag in {"h1", "h2", "h3", "caption"} and self._text is not None:
            text = " ".join("".join(self._text).split())
            (self.captions if tag == "caption" else self.headings).append((tag, text))  # type: ignore[arg-type]
            self._text = None

    def handle_data(self, data: str) -> None:
        if self._text is not None:
            self._text.append(data)


def outline(html: str) -> Outline:
    parser = Outline()
    parser.feed(html)
    parser.close()
    assert parser.stack == []
    return parser


def leaderboard(html: str) -> str:
    match = re.search(r'<table id="leaderboard-table">.*?</table>', html, re.S)
    assert match
    return match.group(0)


def test_document_outline_snapshot() -> None:
    html = render_report(summary(), "html")
    tree = outline(html)
    assert html.startswith('<!doctype html>\n<html lang="en">')
    assert tree.headings == [
        ("h1", "Coding task comparison"),
        ("h2", "Leaderboard"),
        ("h2", "Pass@1 with 95% bootstrap intervals"),
        ("h3", "Paired comparisons"),
        ("h2", "Pass@1 by category"),
        ("h2", "Per-task pass matrix"),
        ("h2", "Timing distribution"),
    ]
    tables = [attrs for tag, attrs in tree.starts if tag == "table"]
    assert len(tree.captions) == len(tables) == 4
    # Every column header and row header declares its scope.
    for tag, attrs in tree.starts:
        if tag == "th":
            assert attrs.get("scope") in {"col", "row"}
    # Scrollable regions are labelled and keyboard focusable.
    regions = [attrs for tag, attrs in tree.starts if attrs.get("role") == "region"]
    assert len(regions) == 4
    assert all(r.get("tabindex") == "0" and r.get("aria-labelledby") for r in regions)


def test_self_contained_with_dark_mode_and_mobile_rules() -> None:
    html = render_report(summary(), "html")
    assert '<meta name="viewport" content="width=device-width, initial-scale=1">' in html
    assert "default-src 'none'" in html
    assert "@media (prefers-color-scheme: dark)" in html
    assert "@media (max-width: 640px)" in html
    assert "overflow-x: auto" in html
    assert html.count("<script>") == 1 and "<link" not in html
    for _, attrs in outline(html).starts:
        assert "src" not in attrs
        assert (attrs.get("href") or "#").startswith("#")
    assert "://" not in html and "url(" not in html and "@import" not in html


def test_hostile_model_names_are_escaped_everywhere() -> None:
    html = render_report(summary(), "html")
    assert "<img" not in html and 'onerror="' not in html
    escaped = "&lt;img src=x onerror=&#34;alert(1)&#34;&gt;&amp;&#34;model&#39;"
    # Leaderboard, CI chart label and aria-label, comparisons, heatmap, matrix, timing chart.
    assert html.count(escaped) >= 8
    assert f'data-value="{escaped.lower()}"' in html
    # Attribute values never break out of their quotes.
    for tag, attrs in outline(html).starts:
        for name in attrs:
            assert name.isascii() and not name.startswith("on"), (tag, name)


def test_escapes_categories_and_task_ids() -> None:
    rows = [
        attempt("m", "<b>task</b>", 1, True, category="<i>cat</i>"),
        attempt("m", "other", 1, False, category="plain"),
    ]
    html = render_report(summarize(rows, (1,)), "html")
    assert "<b>" not in html and "<i>" not in html
    assert "&lt;b&gt;task&lt;/b&gt;" in html and "&lt;i&gt;cat&lt;/i&gt;" in html


def test_unknown_and_partial_usage() -> None:
    html = leaderboard(render_report(summary(), "html"))
    rows = {}
    for row in re.findall(r"<tr>.*?</tr>", html, re.S):
        name = re.search(r'<th scope="row"[^>]*>(.*?)</th>', row)
        if name:
            rows[name.group(1)] = row
    hostile = next(row for key, row in rows.items() if key.startswith("&lt;img"))
    assert hostile.count('<span class="unknown">unknown</span>') == 3
    assert hostile.count('data-value=""') == 3
    assert "unknown" not in rows["reported"] and "reported</small>" not in rows["reported"]
    assert ">60<" in rows["reported"] and ">120<" in rows["reported"] and ">3<" in rows["reported"]
    partial = rows["partial"]
    assert ">15<small>3/6 reported</small>" in partial
    assert ">42<" in partial and "6/6 reported" not in partial
    assert partial.count('<span class="unknown">unknown</span>') == 1  # cost


def test_sort_attributes() -> None:
    html = leaderboard(render_report(summary(), "html"))
    header = re.search(r"<thead>.*?</thead>", html, re.S)
    assert header
    cells = re.findall(r"<th ([^>]*)>(.*?)</th>", header.group(0))
    sortable = {text: attrs for attrs, text in cells if "data-sort=" in attrs}
    assert list(sortable) == [
        "Rank",
        "Model",
        "Pass@1",
        "95% CI",
        "Passes",
        "Mean s",
        "Median s",
        "Input tokens",
        "Output tokens",
        "Cost USD",
    ]
    assert 'data-sort="text"' in sortable["Model"]
    assert all('data-sort="num"' in a for t, a in sortable.items() if t != "Model")
    assert 'data-first="ascending"' in sortable["Mean s"]
    # Server-side order is pass@1 descending, and only that header says so.
    assert [t for a, t in cells if "aria-sort" in a] == ["Pass@1"]
    assert 'aria-sort="descending"' in sortable["Pass@1"]
    body_rows = re.findall(r"<tr>.*?</tr>", html.split("</thead>")[1], re.S)
    assert len(body_rows) == 3
    for row in body_rows:
        # One sort key per sortable column; the unsortable Pass@k cell has none.
        assert row.count("data-value=") == len(sortable)
    values = [float(v) for v in re.findall(r'class="num score" data-value="([^"]+)"', html)]
    assert values == sorted(values, reverse=True)


def test_sort_script_is_progressive_enhancement() -> None:
    html = render_report(summary(), "html")
    script = html.split("<script>")[1].split("</script>")[0]
    assert 'createElement("button")' in script and 'button.type = "button"' in script
    assert 'setAttribute("aria-sort", direction)' in script
    assert "aria-live" in html and 'id="sort-status"' in html
    # Without JavaScript the headers are plain text: no button elements in the markup.
    assert "<button" not in html


def test_ci_error_bars_match_the_intervals() -> None:
    data = summary()
    html = render_report(data, "html")
    for model in data.models:
        low, high = model.pass_at_1_ci
        label = (
            f"pass@1 {format_pct(model.pass_at_1)}, 95% interval "
            f"{format_pct(low)} to {format_pct(high)}"
        )
        assert label in html
        assert f'cx="{6 + model.pass_at_1 * 388}"' in html
        assert f'x1="{6 + low * 388}" y1="10" x2="{6 + high * 388}"' in html
    assert html.count('role="img"') == 2 * len(data.models)


def test_heatmap_cells_carry_the_number_and_band() -> None:
    html = render_report(summary(), "html")
    heatmap = re.search(r'<table class="heatmap">.*?</table>', html, re.S)
    assert heatmap
    cells = re.findall(
        r'<td class="num heat heat-(\d)">([\d.]+%)<small>(\d+/\d+)</small>', heatmap.group(0)
    )
    assert len(cells) == 2 * 3  # two categories x three models
    for band, percent, _ in cells:
        assert int(band) == heat_level(float(percent.rstrip("%")) / 100)
    assert "0–20%" in html and "80–100%" in html


@pytest.mark.parametrize(
    "value,band", [(0.0, 0), (0.199, 0), (0.2, 1), (0.5, 2), (0.79, 3), (0.8, 4), (1.0, 4)]
)
def test_heat_bands(value: float, band: int) -> None:
    assert heat_level(value) == band


def test_missing_cells_are_marked_for_screen_readers() -> None:
    rows = [attempt("a", "p1", 1, True), attempt("b", "a1", 1, True)]
    html = render_report(summarize(rows, (1,)), "html")
    assert html.count('—<span class="visually-hidden">not run</span>') == 4
