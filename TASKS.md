# v1.3.0 upgrade — progress

Branch `upgrade/v1.3.0`. Frozen task: 10 acceptance items. Work is sliced across sessions;
read this file and `HANDOFF.md` first.

| # | Item | Status |
|---|------|--------|
| 1 | Task suite 6 → ≥16 with `category`, bug-fix tasks, refs in `tests/fixtures/reference/`, solvability + empty-stub CI test | TODO — `category` field exists in `TaskSpec`; the 6 existing tasks are tagged (parsing / algorithms / stateful) |
| 2 | Bootstrap 95% CIs (seeded), per-category breakdown, paired comparison notes, unit tests | DONE (slice 1, commit 33ddb4e) |
| 3 | HTML report redesign: sortable leaderboard (no JS libs), category heatmap, SVG CI error bars, unknown usage, a11y, mobile | TODO — slice 1 only added a CI column, category table and comparison notes to the existing template |
| 4 | `cli` runner presets: claude-code, codex, opencode (templates, timeout, workdir isolation, env allow-list) + fake-CLI tests | TODO |
| 5 | CI gates: ruff lint+format, mypy strict, coverage ≥85%, 3.11+3.12 matrix, gitleaks, Dependabot, CodeQL | DONE (slice 1, commit 451988a); CI result: see HANDOFF.md |
| 6 | Measured run v2 (≥4 models × 16 tasks × 3 repeats, <350 attempts) under `results/2026-10-21-measured/` | TODO — needs item 1 first; env has ANTHROPIC_AUTH_TOKEN, not ANTHROPIC_API_KEY (map it in the run shell only) |
| 7 | README refresh (badges, Showcase screenshot, catalogue, mermaid, results, roadmap) | TODO |
| 8 | CHANGELOG 1.3.0, version bump (pyproject, `__init__`), CITATION.cff | TODO |
| 9 | TASKS.md current; HANDOFF.md at end | IN PROGRESS |
| 10 | Push via push.sh, CI green on head, print `PU_DONE` | TODO (slice 1 pushed; final push pending) |

## Plan for item 1 (decided in slice 1)
- Add `starter:` (optional task file) to `TaskSpec` for bug-fix tasks: engine copies it to the
  workdir as the entrypoint before generation; HTTP prompt includes its source; CLI agents edit it.
- Move all references to `tests/fixtures/reference/<task_id>.py`; mock runner gets a
  `reference_dir` option (resolved relative to the config by the engine) so the offline demo keeps working;
  `validate-task --reference PATH`.
- New tasks (10): 2 algorithms, 2 parsing, 2 stateful, 4 bug-fix; ≥8 hidden tests each.
- CI test: every task passes with its reference; 0 tests pass on an empty module and on a
  `__getattr__`-returns-None stub; each bug-fix starter fails ≥1 and passes ≥1 hidden test.
