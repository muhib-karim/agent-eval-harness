# Project brain — agent-eval-harness

Handoff note for the next session. Detailed progress: `TASKS.md`; session report: `HANDOFF.md`.

## Status
v1.3.0 upgrade on branch `upgrade/v1.3.0`. Done: items 1 (16 tasks), 2 (bootstrap CIs),
3 (self-contained accessible HTML report), 4 (agent CLI presets), 5 (CI gates), 8 (CHANGELOG,
version 1.3.0), SKILLS_USED.md. Slice 3 commits are local, not pushed.

## Next step
Item 6 (live run on 16 tasks, background + log), then 7 (README, screenshot of the new report),
then push and CI (10).

## Gotchas
- Run pytest as `setsid -w timeout -k 5 300 pytest -x -q -p no:cacheprovider` (one process only;
  without `-w`, setsid can fork and return before the run finishes).
- Hidden tests must fail on a stub whose calls return None: `pytest.raises(TypeError/AttributeError)`
  alone is vacuous, so exercise the object first.
- Results schema is additive only: `Attempt.category` is optional so older result files load.
- Scrub absolute paths from `metadata.json` / `config.resolved.yaml` before committing a run.

## Session log
- 2026-10-21 09:50Z Claude Code / claude-opus-5-5: slice 1 — stats (CIs, categories, paired notes) and CI gates; next: item 1.
- 2026-10-21 16:15Z Claude Code / claude-opus-5-5: slice 2 — items 1 and 4 (16 tasks, starters, reference_dir, CLI presets); 205 tests, 98.9% cov; not pushed; next: item 3.
- 2026-10-21 16:45Z Claude Code / claude-opus-5-5: slice 3 — items 3 and 8, SKILLS_USED.md; 222 tests, 98.9% cov; not pushed; next: item 6.
