# v1.3.0 upgrade — progress

Branch `upgrade/v1.3.0`. Frozen task: 10 acceptance items. Work is sliced across sessions;
read this file and `HANDOFF.md` first.

| # | Item | Status |
|---|------|--------|
| 1 | Task suite 6 → ≥16 with `category`, bug-fix tasks, refs in `tests/fixtures/reference/`, solvability + empty-stub CI test | DONE (slice 2, commits d5445f4, f6d143c, 91769e3): 16 tasks, 4 per category; `tests/test_task_suite.py` |
| 2 | Bootstrap 95% CIs (seeded), per-category breakdown, paired comparison notes, unit tests | DONE (slice 1, commit 33ddb4e) |
| 3 | HTML report redesign: sortable leaderboard (no JS libs), category heatmap, SVG CI error bars, unknown usage, a11y, mobile | DONE (slice 3, commit b670efd): self-contained template, `tests/test_report_html.py`; 17 Oct `report.md` regenerated (8c989a4) |
| 4 | `cli` runner presets: claude-code, codex, opencode (templates, timeout, workdir isolation, env allow-list) + fake-CLI tests | DONE (slice 2, commits 4661743, fc6f2eb): `runners/presets.py`, `tests/test_cli_presets.py`, docs + `examples/agent-clis.yaml` |
| 5 | CI gates: ruff lint+format, mypy strict, coverage ≥85%, 3.11+3.12 matrix, gitleaks, Dependabot, CodeQL | DONE (slice 1, commit 451988a); CI 39579363695 and CodeQL 39579363919 green on 611997a |
| 6 | Measured run v2 (≥4 models × 16 tasks × 3 repeats, <350 attempts) under `results/2026-10-21-measured/` | TODO — unblocked (item 1 done); 4 models × 16 × 3 = 192 attempts; env has ANTHROPIC_AUTH_TOKEN, not ANTHROPIC_API_KEY (map it in the run shell only) |
| 7 | README refresh (badges, Showcase screenshot, catalogue, mermaid, results, roadmap) | TODO |
| 8 | CHANGELOG 1.3.0, version bump (pyproject, `__init__`), CITATION.cff | DONE (slice 3, commit 70b4233): `## [1.3.0] - 2026-10-21` incl. the env allow-list behaviour change; pyproject, `__init__`, CITATION.cff at 1.3.0. Add the measured run v2 to the CHANGELOG when item 6 lands |
| 9 | TASKS.md current; HANDOFF.md at end | IN PROGRESS |
| 10 | Push via push.sh, CI green on head, print `PU_DONE` | TODO — slices 1–2 pushed (head e346a95); slice 3 commits are local only (not pushed, per slice instructions) |
| — | SKILLS_USED.md "v1.3.0" section | DONE (slice 3, commit 167a4b0); extend it as later slices load skills |

## Item 1 as built (slice 2)
- `TaskSpec.starter`: copied to the entrypoint before generation; embedded in HTTP prompts;
  CLI agents edit it in place; hashed into provenance.
- All 16 references in `tests/fixtures/reference/<task_id>.py`; mock runner `reference_dir`
  (resolved against the config dir) keeps the offline demo working; `validate-task --reference`.
- New tasks: topo_sort, levenshtein (algorithms); semver, ini_parser (parsing); undo_buffer,
  ledger (stateful); fix_binary_search, fix_running_stats, fix_memoize, fix_slugify (bug-fix).
- `tests/test_task_suite.py`: reference passes with >= 8 tests; 0 tests pass on an empty module
  and on a `__getattr__`-returns-None stub (all 16 tasks, old ones included); each starter
  fails >= 1 and passes >= 1. The stub check caught two vacuous tests while authoring.

## Next slice
Item 6 (live run: 4 models × 16 tasks × 3 repeats = 192 attempts, background + log), then 7 (README:
badges, Showcase screenshot of the NEW report rendered headless into `docs/assets/`, catalogue,
mermaid, results; update the v1.2.0 wheel install line once v1.3.0 is released; refresh
`docs/sample-report.md`, which still shows the old 6-task mock demo), Pages landing to the new run
with the 17 Oct run linked as history, then 9 and 10.
