# Project brain — agent-eval-harness

Handoff note for the next session. Detailed progress: `TASKS.md`; session report: `HANDOFF.md`.

## Status
v1.3.0 upgrade on branch `upgrade/v1.3.0`. Slice 1 done: bootstrap CIs + per-category
breakdown (item 2) and CI quality gates (item 5).

## Next step
Item 1 (task suite to ≥16 with categories, bug-fix tasks, external references), following the
plan in `TASKS.md`. Then items 3, 4, 6, 7, 8.

## Gotchas
- Run pytest as `setsid timeout -k 5 300 pytest -x -q -p no:cacheprovider` (one process only).
- Results schema is additive only: `Attempt.category` is optional so older result files load.
- Scrub absolute paths from `metadata.json` / `config.resolved.yaml` before committing a run.

## Session log
- 2026-10-21 09:50Z Claude Code / claude-opus-5-5: slice 1 — stats (CIs, categories, paired notes) and CI gates; next: item 1.
