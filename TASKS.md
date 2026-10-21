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
| 6 | Measured run v2 (≥4 models × 16 tasks × 3 repeats, <350 attempts) under `results/2026-10-21-measured/` | DONE (slice 4, commit b4fdb7c): 6 models × 16 × 3 = 288 attempts, 2026-10-21 17:53–18:11Z, 261 pass; METHODOLOGY.md; `--resume` added (5ec4dd7), not needed |
| 7 | README refresh (badges, Showcase screenshot, catalogue, mermaid, results, roadmap) | DONE (slice 4, commits 5ae78cf, 249e351, 5f24a6d, d8d0552, 722649a): README, screenshot, sample report, CONTRIBUTING, reference docs, CHANGELOG |
| 8 | CHANGELOG 1.3.0, version bump (pyproject, `__init__`), CITATION.cff | DONE (slice 3, commit 70b4233): `## [1.3.0] - 2026-10-21` incl. the env allow-list behaviour change; pyproject, `__init__`, CITATION.cff at 1.3.0; measured run v2, `--resume` and README changes added (722649a); release notes `RELEASE_NOTES_v1.3.0.md` (2227349) |
| 9 | TASKS.md current; HANDOFF.md at end | DONE (slice 5): HANDOFF.md final, with RUN vs INFERRED checks, CI run ids and the model used (claude-opus-5-5) |
| 10 | Push via push.sh, CI green on head, print `PU_DONE` | HANDED OFF — slices 1–4 pushed (head 4e48f9b: CI 39651870067 and CodeQL 39651870150 green, all 5 CI jobs). Slice 5 commits are local; per instructions the coordinator pushes, opens the PR, merges and tags v1.3.0 |
| — | SKILLS_USED.md "v1.3.0" section | DONE (slice 3, commit 167a4b0; slice 4 entries c98eaa8) |

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

## Next steps (coordinator)
1. Push the branch and confirm CI, CodeQL and gitleaks are green on the new head.
2. Open the PR to `main`, review, merge.
3. Tag `v1.3.0` on the merge commit: the release workflow publishes the wheel, sdist,
   `SHA256SUMS.txt` and `RELEASE_NOTES_v1.3.0.md`; the README install line works from then on.
4. Pages deploys from `main` with the 21 Oct run as the landing page.

Known follow-ups are listed in HANDOFF.md under "Remaining issues".
