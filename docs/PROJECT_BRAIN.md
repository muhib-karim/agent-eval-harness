# Project brain — agent-eval-harness

Handoff note for the next session. Detailed progress: `TASKS.md`; session report: `HANDOFF.md`.

## Status
v1.3.0 upgrade on branch `upgrade/v1.3.0` is complete (items 1–9). Release notes written.
Slices 1–4 are pushed and green (4e48f9b); the slice 5 commits are local, for the coordinator to
push, merge and tag.

## Next step
Coordinator: push, PR, merge, tag v1.3.0. After that, the follow-ups in HANDOFF.md: a stricter
code-block extraction for single-block prompts, recording `stop_reason`, and harder tasks to
separate the top models.

## Gotchas
- Run pytest as `setsid -w timeout -k 5 300 pytest -x -q -p no:cacheprovider` (one process only;
  without `-w`, setsid can fork and return before the run finishes).
- Hidden tests must fail on a stub whose calls return None: `pytest.raises(TypeError/AttributeError)`
  alone is vacuous, so exercise the object first.
- CodeQL ignores results/** and tasks/*/starter.py (.github/codeql/codeql-config.yml); hidden tests are hashed by measured runs, so do not edit them to silence alerts.
- Results schema is additive only: `Attempt.category` is optional so older result files load.
- Scrub absolute paths from `metadata.json` / `config.resolved.yaml` (and test logs) before committing a run.
- The live endpoint's base URL variable lacks the API version path; append it in the run shell only.

## Session log
- 2026-10-21 09:50Z Claude Code / claude-opus-5-5: slice 1 — stats (CIs, categories, paired notes) and CI gates; next: item 1.
- 2026-10-21 16:15Z Claude Code / claude-opus-5-5: slice 2 — items 1 and 4 (16 tasks, starters, reference_dir, CLI presets); 205 tests, 98.9% cov; not pushed; next: item 3.
- 2026-10-21 16:45Z Claude Code / claude-opus-5-5: slice 3 — items 3 and 8, SKILLS_USED.md; 222 tests, 98.9% cov; not pushed; next: item 6.
- 2026-10-21 18:20Z Claude Code / claude-opus-5-5: slice 4 — --resume, measured run v2 (288 attempts), README/docs refresh; 229 tests, 98.9% cov; not pushed; next: push + CI.
- 2026-10-21 18:25Z Claude Code / claude-opus-5-5: slice 5 — release notes, release workflow uses them, final HANDOFF/TASKS; 229 tests, 98.9% cov, gitleaks clean; not pushed.
- 2026-10-21 18:40Z Claude Code / claude-opus-5-5: slice 6 — CodeQL config (paths-ignore results/**, starters), fixed 5 harness alerts, docs; 229 tests, gitleaks clean; not pushed.
