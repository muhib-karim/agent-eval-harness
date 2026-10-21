import pytest

from agent_eval.report import render_report
from agent_eval.results import Attempt, summarize
from agent_eval.stats import bootstrap_mean_ci, paired_bootstrap_diff, percentile


def make(model: str, task: str, repeat: int, passed: bool, category: str | None) -> Attempt:
    return Attempt(
        attempt_id=f"{model}-{task}-{repeat}",
        model=model,
        runner="mock",
        task_id=task,
        repeat=repeat,
        outcome="pass" if passed else "fail",
        wall_time_s=1,
        generation_time_s=1,
        grading_time_s=0,
        artifacts="x",
        category=category,
    )


def test_percentile_interpolates_and_validates() -> None:
    assert percentile([0.0, 1.0], 0.5) == 0.5
    assert percentile([0.0, 1.0, 2.0], 1) == 2.0
    assert percentile([3.0], 0.25) == 3.0
    with pytest.raises(ValueError):
        percentile([], 0.5)
    with pytest.raises(ValueError):
        percentile([1.0], 1.5)


def test_bootstrap_is_deterministic_with_a_seed() -> None:
    values = [0.0, 1.0, 1.0, 0.5, 1 / 3, 0.0, 1.0]
    first = bootstrap_mean_ci(values, seed=7, resamples=500)
    assert first == bootstrap_mean_ci(values, seed=7, resamples=500)
    assert first != bootstrap_mean_ci(values, seed=8, resamples=500)
    low, high = first
    assert 0 <= low <= sum(values) / len(values) <= high <= 1


def test_bootstrap_degenerate_and_invalid_inputs() -> None:
    assert bootstrap_mean_ci([1.0, 1.0, 1.0]) == (1.0, 1.0)
    assert bootstrap_mean_ci([0.25]) == (0.25, 0.25)
    with pytest.raises(ValueError):
        bootstrap_mean_ci([])
    with pytest.raises(ValueError):
        bootstrap_mean_ci([1.0], resamples=0)
    with pytest.raises(ValueError):
        bootstrap_mean_ci([1.0], confidence=1)


def test_wider_confidence_gives_wider_interval() -> None:
    values = [0.0, 1.0] * 6
    narrow = bootstrap_mean_ci(values, confidence=0.5)
    wide = bootstrap_mean_ci(values, confidence=0.99)
    assert wide[0] <= narrow[0] and narrow[1] <= wide[1]


def test_paired_diff_uses_shared_tasks_only() -> None:
    diff, low, high = paired_bootstrap_diff({"a": 1.0, "b": 1.0, "c": 0.0}, {"a": 0.0, "b": 0.0})
    assert diff == 1.0 and low == high == 1.0
    with pytest.raises(ValueError):
        paired_bootstrap_diff({"a": 1.0}, {"b": 1.0})


def test_summary_has_seeded_ci_and_category_breakdown() -> None:
    rows = [
        make("m", "t1", 1, True, "algorithms"),
        make("m", "t1", 2, False, "algorithms"),
        make("m", "t2", 1, True, "algorithms"),
        make("m", "t2", 2, True, "algorithms"),
        make("m", "t3", 1, False, None),
        make("m", "t3", 2, False, None),
    ]
    summary = summarize(rows, (1,), seed=3, resamples=300)
    model = summary.models[0]
    assert summary.bootstrap.seed == 3 and summary.bootstrap.resamples == 300
    assert summary.task_categories == {
        "t1": "algorithms",
        "t2": "algorithms",
        "t3": "uncategorized",
    }
    low, high = model.pass_at_1_ci
    assert low <= model.pass_at_1 == 0.5 <= high
    assert model.pass_at_1_ci == summarize(rows, (1,), seed=3, resamples=300).models[0].pass_at_1_ci
    by_name = {c.category: c for c in model.categories}
    assert by_name["algorithms"].tasks == 2
    assert by_name["algorithms"].pass_at_1 == 0.75
    assert (by_name["uncategorized"].passed, by_name["uncategorized"].attempts) == (0, 2)


def test_conflicting_categories_are_rejected() -> None:
    rows = [make("m", "t", 1, True, "a"), make("n", "t", 1, True, "b")]
    with pytest.raises(ValueError, match="conflicting categories"):
        summarize(rows)


def test_overlapping_models_get_a_paired_note() -> None:
    tasks = [f"t{i}" for i in range(8)]
    rows = [make("strong", t, 1, True, "x") for t in tasks]
    rows += [make("weak", t, 1, i != 0, "x") for i, t in enumerate(tasks)]
    rows += [make("zero", t, 1, False, "x") for t in tasks]
    summary = summarize(rows, (1,))
    pairs = {(c.model_a, c.model_b): c for c in summary.comparisons}
    # "zero" never overlaps the others, so it is not compared.
    assert set(pairs) == {("strong", "weak")}
    note = pairs["strong", "weak"]
    assert note.shared_tasks == 8 and note.diff == pytest.approx(1 / 8)
    assert not note.significant and "includes zero" in note.note
    markdown = render_report(summary, "md")
    assert "Paired comparisons" in markdown and "95% CI" in markdown
    assert "Pass@1 by category" in markdown
    html = render_report(summary, "html")
    assert "Pass@1 by category" in html and "no reliable difference" in html


def test_significant_paired_difference_is_reported() -> None:
    # "a" passes exactly one more of four repeats than "b" on every task, while tasks vary
    # widely in difficulty: marginal intervals overlap but the paired difference does not.
    bases = [0, 0, 1, 1, 2, 2, 3, 3, 0, 1]
    rows = [
        make(name, f"t{i}", r, r <= base + bonus, "x")
        for name, bonus in (("a", 1), ("b", 0))
        for i, base in enumerate(bases)
        for r in range(1, 5)
    ]
    summary = summarize(rows, (1,))
    [comparison] = summary.comparisons
    assert comparison.significant and comparison.diff == pytest.approx(0.25)
    assert "excludes zero" in comparison.note
    assert "<strong>differs</strong> (interval excludes 0)" in render_report(summary, "html")


def test_old_results_without_category_still_load() -> None:
    line = make("m", "t", 1, True, None).model_dump()
    del line["category"]
    assert Attempt.model_validate(line).category is None
