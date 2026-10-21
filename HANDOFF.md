# Handoff: v1.3.0 upgrade (in progress)

Branch `upgrade/v1.3.0`. Model used in these sessions: **claude-opus-5-5** (Claude Code).
Status by item: see `TASKS.md`. Items 1–8 are done; only the final push with green CI (10) remains.

## What changed

### Slice 1 (pushed, head 611997a)
- `stats.py`: seeded task-level percentile bootstrap (seed 20261021, 2000 resamples, 95%) for
  pass@1; paired bootstrap of the difference for every model pair whose intervals overlap.
- `Summary` gains `pass_at_1_ci`, per-category scores, `task_categories`, `bootstrap`,
  `comparisons`. `Attempt.category` is optional (additive); old result files load as
  `uncategorized`. `report --seed/--resamples`. Markdown and HTML show CIs, categories, notes.
- CI: named lint/format/strict-mypy steps, coverage gate (85%) with summary and artifact,
  pinned gitleaks job, CodeQL workflow, Dependabot (pip + github-actions).

### Slice 2 (pushed, head e346a95)
- Bug-fix task support (`starter:`), mock `reference_dir`, `validate-task --reference`.
- References moved out of task directories to `tests/fixtures/reference/` (mypy excludes them).
- 10 new tasks → 16 total, 4 per category (algorithms, parsing, stateful, bug-fix), each with
  >= 8 hidden tests; `tests/test_task_suite.py` enforces solvability and non-vacuous tests.
- `cli` runner presets `claude-code`, `codex`, `opencode`; environment allow-list for every
  CLI agent; `isolate_home`; `{prompt}` placeholder; claude-code JSON usage parsing;
  redaction of forwarded credential values. Docs in `docs/reference.md`,
  `examples/agent-clis.yaml`.

### Slice 3 (pushed, head 187a051; CI 39635710585 and CodeQL 39635710548 green)
- HTML report redesigned as one self-contained file (CSP `default-src 'none'`, no external
  assets): leaderboard sortable by a ~40-line inline script that turns headers into
  keyboard-operable buttons and moves `aria-sort` (a plain table, ordered by pass@1, without
  JavaScript; unknown values sort last; a live region announces each sort); per-model SVG
  interval rows; a paired-comparison table; category heatmap and per-task matrix with the number in
  every cell and contrast-checked colour bands; `unknown` / `n/N reported` usage; captions,
  scoped headers, labelled focusable scroll regions, skip link; dark mode; 375 px layout.
- `tests/test_report_html.py` (snapshot-style: outline, self-containment, escaping incl.
  attributes, unknown/partial usage, sort attributes, CI geometry, heat bands).
- `results/2026-10-17-measured/report.md` regenerated from the unchanged `results.jsonl`.
- CHANGELOG `## [1.3.0] - 2026-10-21` (Keep a Changelog), version 1.3.0 in pyproject,
  `__init__` and CITATION.cff (date 2026-10-21). `SKILLS_USED.md` created.

### Slice 4 (local commits 5ec4dd7..HEAD, NOT pushed per the slice instructions)
- `agent-eval run --resume`, with `tests/test_resume.py`.
- Measured run v2 in `results/2026-10-21-measured/`: claude-opus-5-5, claude-fable-5-1,
  claude-sonnet-5-5, claude-sonnet-5, claude-haiku-4-5 (Messages API) and gpt-6-sol (Chat
  Completions), 16 tasks, 3 repeats, 288 attempts, 2026-10-21 17:53:41Z to 18:11:34Z, uninterrupted.
  pass@1: 100 / 100 / 100 / 97.9 / 79.2 / 66.7%. 27 non-passing attempts (16 fail, 8 error,
  3 timeout), none retried, all explained in `METHODOLOGY.md`. claude-haiku-4-5 answered too
  but was left out to stay under the attempt budget.
- Run hygiene: the key mapping and the API version path for the base URL existed only in a
  scratch launcher's environment. Output went to scratch, was copied with machine paths replaced
  (repo root, one temp workdir in a test log), then scanned for machine paths, endpoint hosts and
  credentials (none). The reports were regenerated with `--k 1 --k 3`, and task and config hashes
  were verified against the repository.
- Pages workflow: the landing page is the new run (plus METHODOLOGY.md); the 17 Oct run is under
  `/history/2026-10-17/`.
- README rewritten (badges, Showcase screenshot `docs/assets/report-2026-10-21.png` rendered with
  headless Chromium, quickstart, usage, task catalogue, Mermaid architecture, results, roadmap,
  links). The release install line now targets v1.3.0 with the `grade` extra. The stale
  `docs/assets/demo-report.png` was removed. `docs/sample-report.md` (16-task demo),
  CONTRIBUTING, `docs/reference.md` and the CHANGELOG were updated.

## Checks

RUN (slice 4, before the handoff commit):
- `ruff check .`, `ruff format --check .` → clean. `mypy --strict` → no issues in 29 source files.
- `pytest -x -q -p no:cacheprovider` → 229 passed in 100.77s; coverage 98.94% (gate 85%).
- Live run: 288/288 attempts recorded, `agent-eval` exit 0; log lines `start 2026-10-21T17:53:41Z`,
  `Completed 288 attempts; 261 passed.`, `exit 0 2026-10-21T18:11:34Z`.
- `metadata.json` hashes: 36 task files and the config hash match the repository.
- Scrub check: no machine paths, endpoint hosts or credentials in `results/2026-10-21-measured/`;
  `gitleaks dir` on it → no leaks.
- A fresh venv with `pip install '.[grade]'` (non-editable) → `agent-eval --version` 1.3.0;
  `list-tasks` lists 16 tasks.
- Every README finding was checked against `results.jsonl`; one overstatement was corrected.

RUN (slice 3, Python 3.11.6, before the handoff commit):
- `ruff check .`, `ruff format --check .` → clean. `mypy --strict` → no issues in 28 source files.
- `pytest -x -q -p no:cacheprovider` → 222 passed in 90.88s; coverage 98.89% (gate 85%).
- Headless Chromium renders of the report at 1280 px and 375 px, light and dark: inspected by eye;
  fixed misaligned interval gridlines, leaderboard overflow and clipped mobile captions.
- Scripted sort check in headless Chromium (injected clicks on a scratch copy): 10 header buttons
  created; Model sorts ascending then descending; Mean s ascending; `aria-sort` moves to the
  clicked header only; an all-unknown Cost column keeps a stable order; the live region reads
  "Sorted by Cost USD, ascending."
- `agent-eval --version` → 1.3.0. gitleaks and forbidden-term grep: see below.

RUN (slice 2, Python 3.11.6, head fc6f2eb):
- `ruff check .` → All checks passed. `ruff format --check .` → clean.
- `mypy --strict` → Success: no issues found in 27 source files.
- `pytest -x -q -p no:cacheprovider` → 205 passed in 81.30s; coverage 98.89% (gate 85%).
- `agent-eval run examples/mock-demo.yaml` → 64 attempts, 32 passed; mock-reference 100% in all
  4 categories, mock-wrong 0%.
- Every bug-fix starter graded against its hidden tests: fix_binary_search 5/12,
  fix_running_stats 9/13, fix_memoize 6/10, fix_slugify 11/13 (outcome `fail` each).
- `gitleaks git` on 611997a..HEAD and `gitleaks dir .` → no leaks found. Grep of added lines for
  forbidden terms, machine paths and URLs → no hits. Endpoint hosts/credentials from the
  environment → not present in the tree. Commit author/committer identity → correct for all.
- Slice 1 CI on GitHub: CI run 39579363695 success, CodeQL run 39579363919 success (head 611997a).

INFERRED (not run):
- `pipx install '.[grade]'` (pipx is not installed on this machine; the plain pip path was run).
- The Mermaid diagram rendering on GitHub (syntax kept to basic flowchart features; not rendered
  locally). The Pages workflow change (it runs only on `main`).
- The README release install line resolves only after `v1.3.0` is tagged and the release
  workflow attaches the wheel.
- Screen-reader output of the report (structure checked by tests and by reading the markup, not
  with NVDA/VoiceOver). Contrast ratios were computed from the colour tokens, not measured with
  an automated checker such as axe.
- Python 3.12 locally (CI matrix covers it once pushed); the Docker and offline-demo CI jobs for
  slice 2 (they run `examples/mock-demo.yaml`, whose `reference_dir` resolves inside the copied
  repo, so they should pass).
- The preset command templates against the real claude / codex / opencode binaries. They follow
  the CLIs' documented headless modes but were exercised only with a fake CLI.

## Remaining issues / notes
- Behaviour change to record in the CHANGELOG (item 8): CLI agents no longer inherit the whole
  parent environment; they get the allow-list plus `env_passthrough`.
- When an HTTP runner errors on a bug-fix task, the saved `solution.py` artifact is the
  untouched starter (the outcome is still correctly `error`). Possible follow-up: skip saving
  the solution when it is byte-identical to the starter, or label it.
- Extraction rule: replies with several Python blocks are joined (documented). For single-block
  prompts this turned four claude-haiku-4-5 replies into import errors. A stricter rule, such as
  taking the largest block when the prompt asks for one block, is on the roadmap; it was not
  applied to this run's results.
- The HTTP runner does not record the provider's stop reason, so "used the whole output budget"
  is inferred from reported output tokens equal to `max_tokens`. Recording `stop_reason` would be
  a small additive schema extension.
- The coverage badge is a static number (98.9%) from this slice's local run; CI enforces the 85% gate.
- HANDOFF.md was not written at the end of slice 1 (that session hit its time box after the push);
  this file covers both slices.
