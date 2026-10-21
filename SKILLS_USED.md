# Skills used

Which agent skills drove which change. "Invoked" means the skill's instructions were loaded and
followed in the session; "practice" means the work followed a similar discipline without loading
a skill. Nothing is listed that did not happen.

## v1.3.0

Sessions: Claude Code, model `claude-opus-5-5`, 2026-10-21, in slices.

### Invoked

| Skill | Slice | What it drove |
| --- | --- | --- |
| `frontend-ui-engineering` | 3 | The HTML report redesign (`src/agent_eval/templates/report.html`). Its "avoid the AI aesthetic" table set the constraints: no gradients, shadows or decorative icons; the project's existing ink/teal palette as semantic tokens; a 4 px radius used once. Its accessibility section drove the scoped headers, captions, labelled focusable scroll regions, skip link, real `<button>` sort controls, `aria-sort`, a live region, and colour never carrying meaning alone (every heatmap cell prints its number). Its verification checklist drove rendering the page in headless Chromium at 1280 px and 375 px, in light and dark mode, and a scripted click test of the sort. Those renders exposed three layout bugs, all fixed before commit: misaligned interval gridlines across rows, an overflowing leaderboard, and captions clipped on mobile. |

### Practice, without loading a skill

| Discipline | Where |
| --- | --- |
| Verification before claiming completion | Every slice ran ruff, `ruff format --check`, `mypy --strict` and the full pytest suite with the coverage gate before committing, and recorded the outputs in `HANDOFF.md`. |
| Tests that prove the tests | `tests/test_task_suite.py` grades every task's hidden tests against an empty module and a `None`-returning stub. This found two vacuous tests (`fix_memoize`, `undo_buffer`) during authoring; both were fixed. Each bug-fix starter is checked to fail some tests and pass others. |
| Systematic debugging | A wrong expected value in the `fix_running_stats` issue text (24.8; the sample variance is 25.1) was found by grading the reference, checked by hand, and fixed in both the prompt and the test. |
| Systematic debugging (slice 4) | Before the live run, every Messages-API model returned HTTP 404 on a probe, including models that should exist. That pointed to the request path, not the models: the base URL lacked the API version path, so the fix went into the run environment and no code changed. During the run, `model returned empty code` errors were traced to 0-byte replies whose reported output tokens equal the 8192 budget. Four other errors were traced to multi-block replies meeting the documented join-all-blocks extraction rule. Both are reported, not patched after the fact. |
| Verification before completion (slice 4) | Every README finding was checked against `results.jsonl` before commit. This caught one false claim ("more than twice any other model's output tokens"; the real ratio is 1.7×), which was corrected. Task and config hashes in the committed `metadata.json` were re-verified against the repository, and the scrubbed results were scanned for machine paths, endpoint hosts and credentials. |
| Self review of the diff | Done before each handoff; one finding (a bug-fix attempt that errors keeps the untouched starter as its `solution.py` artifact) is recorded in `HANDOFF.md` as an open note. |

### Named in the task but not used (so far)

- `brainstorming`, `writing-plans`: the plan was written directly into `TASKS.md`.
- `test-driven-development`: tests were written alongside or right after the code, not strictly
  red-green-refactor first.
- `requesting-code-review`: no separate reviewer pass yet; only self review.
- `ui-ux-pro-max`, `impeccable`: not loaded; `frontend-ui-engineering` covered the report.
- `understand`, `graphify`, `archify`: not loaded. The README architecture diagram (item 7) was
  updated by hand in Mermaid from the module layout.
- Slice 4 (measured run, README) loaded no skill; the entries above marked slice 4 are practice.
