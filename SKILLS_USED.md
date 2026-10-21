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
| Self review of the diff | Done before each handoff; one finding (a bug-fix attempt that errors keeps the untouched starter as its `solution.py` artifact) is recorded in `HANDOFF.md` as an open note. |

### Named in the task but not used (so far)

- `brainstorming`, `writing-plans`: the plan was written directly into `TASKS.md`.
- `test-driven-development`: tests were written alongside or right after the code, not strictly
  red-green-refactor first.
- `requesting-code-review`: no separate reviewer pass yet; only self review.
- `ui-ux-pro-max`, `impeccable`: not loaded; `frontend-ui-engineering` covered the report.
- `understand`, `graphify`, `archify`: reserved for the README architecture section (item 7),
  not started.
