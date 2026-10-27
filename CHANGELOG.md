# Changelog

All notable changes are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Container-per-attempt isolation: `agent-eval run --isolation docker`, or a top-level
  `isolation:` block in the run config (the flag overrides `isolation.mode`). The `cli` agent
  command and the hidden-test grading each run in a fresh container with no network (`bridge` is
  an explicit opt-in), memory (`2g`, no extra swap), CPU (`2`) and PIDs (`256`) limits, a
  read-only root filesystem, the workdir mounted read-write at `/work`, a `/tmp` tmpfs, all
  capabilities dropped, `no-new-privileges` and the host uid:gid. Environment variables are passed
  by name only, and a timed-out attempt's container is killed. Grading uses the image's `python`,
  which needs pytest (the default `python:3.12-slim` does not have it; the harness image does).
- If docker is missing or its daemon is unreachable, the run falls back to the local runner, prints
  one warning and records it on every attempt.

### Changed

- The results JSONL gains an optional `isolation` field (`requested`, `used`, `warning`). The
  change is additive: older result files still load, resume and report, and `schema_version`
  stays `"1.0"`.

## [1.3.0] - 2026-10-21

### Added

- Task suite grown from 6 to 16 tasks in four categories (`algorithms`, `parsing`, `stateful`,
  `bug-fix`), four tasks each. New: `topo_sort`, `levenshtein`, `semver`, `ini_parser`,
  `undo_buffer`, `ledger` (thread-safe), and bug-fix tasks `fix_binary_search`,
  `fix_running_stats`, `fix_memoize`, `fix_slugify`. Every new task has at least 8 hidden tests.
- `category` field in `task.yaml`; `starter` field for bug-fix tasks (the buggy module is placed
  at the entrypoint before generation and embedded in HTTP prompts).
- `tests/test_task_suite.py`: every bundled task passes with its reference, no hidden test passes
  on an empty module or on a stub that returns `None` for every call, and every bug-fix starter
  fails some hidden tests while passing others.
- Statistics: seeded task-level percentile bootstrap 95% intervals for pass@1 (seed 20261021,
  2000 resamples), per-category pass@1, and a paired bootstrap comparison for every model pair
  whose intervals overlap. `agent-eval report --seed/--resamples`.
- HTML report redesign: one self-contained file with no external assets, a leaderboard sortable
  by keyboard-operable headers (works as a plain table without JavaScript), inline SVG interval
  bars, a category heatmap with the number in every cell, explicit `unknown` usage, dark mode and
  a mobile layout. Markdown and JSON reports carry the intervals, categories and comparisons.
- `cli` runner presets `claude-code`, `codex` and `opencode` (command template, 600 s default
  timeout, forwarded credential names, `executable`/`model`/`extra_args` overrides), a
  `{prompt}` placeholder, `isolate_home` for an empty private `HOME`, and token/cost parsing from
  Claude Code's JSON output. Tested with a fake CLI.
- Mock runner `reference_dir` option; `agent-eval validate-task --reference PATH`.
- `agent-eval run --resume` continues an interrupted run: it requires an unchanged config and task
  hashes, keeps every recorded attempt (errors included) and runs only the missing ones.
- Second measured run, 21 October 2026: six models × 16 tasks × three repeats (288 attempts)
  under `results/2026-10-21-measured/`, with reports and a `METHODOLOGY.md` that records model
  selection and every failure. The README and the Pages landing page show it; the 17 October run
  stays published under `/history/2026-10-17/`.
- CI quality gates: named ruff lint/format and strict mypy steps, coverage summary and artifact
  (gate stays at 85%), a gitleaks job, a CodeQL workflow and Dependabot for pip and GitHub
  Actions. CodeQL skips recorded model outputs (`results/**`) and the deliberately buggy bug-fix
  starters via `.github/codeql/codeql-config.yml`; findings in the harness code were fixed.

### Changed

- **Behaviour change:** CLI agents no longer inherit the whole parent environment. They receive
  an allow-list: `PATH`, `HOME`, `LANG`, `LC_ALL`, `TERM`, `TMPDIR`, `USER`, `SYSTEMROOT`, the
  selected preset's credential variables, and any names listed in the new `env_passthrough`
  option. Configs whose agent relied on another variable must add it to `env_passthrough`.
  Values of forwarded variables (8+ characters) are redacted from saved artifacts.
- Reference solutions moved out of the shipped task directories to
  `tests/fixtures/reference/<task_id>.py`; the offline demo reads them through `reference_dir`.
- The results JSONL gains an optional `category` field. The change is additive: older result
  files still load (as `uncategorized`) and `schema_version` stays `"1.0"`.
- README rewritten around the new run: badges, a Showcase screenshot of the new report, a task
  catalogue and an updated architecture diagram. The release install line includes the `grade`
  extra, which grading needs. `docs/sample-report.md` now shows the 16-task demo.
- `results/2026-10-17-measured/report.md` regenerated from the unchanged `results.jsonl` with
  the new statistics; no measured value changed.

## [1.2.0] - 2026-10-18

- First measured live-model run: six models, six tasks, three repeats (108 attempts), committed
  with every attempt's evidence under `results/2026-10-17-measured/` and summarised in the README.
- HTTP runner option `token_param` (`max_tokens` or `max_completion_tokens`) for OpenAI-compatible
  models that reject `max_tokens`.
- The GitHub Pages site now leads with the measured report; the offline mock demo moved to `/demo/`.
- `CITATION.cff`.

## [1.1.0] - 2026-10-03

- Result loading rejects impossible records: `tests_passed` greater than `tests_total`, and
  duplicate model/task/repeat samples that would inflate pass@k.
- New tests for both checks.
- CI publishes the offline demo's HTML report to GitHub Pages on every push to `main`.
- Package metadata: author and project URLs.

## [1.0.0] - 2026-09-29

- CLI (`run`, `report`, `list-tasks`, `validate-task`) and typed library.
- Runners: Chat Completions-compatible HTTP, Messages API HTTP, external CLI command, offline mock.
- Hidden pytest files copied in after generation; grading in a separate interpreter with
  timeouts and process-group cleanup.
- Versioned JSONL results, resolved config, SHA-256 provenance, per-attempt artifacts, key
  redaction.
- Task-macro pass@1 and unbiased pass@k, timing, and reported-only usage and cost.
- HTML, Markdown and JSON reports.
- Six tasks with reference solutions and hidden tests.
- CI on Python 3.11 and 3.12, offline demo job, non-root Docker image.

The JSONL results carry `schema_version: "1.0"`; a breaking change to that format will bump it.

[1.3.0]: https://github.com/muhib-karim/agent-eval-harness/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/muhib-karim/agent-eval-harness/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/muhib-karim/agent-eval-harness/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/muhib-karim/agent-eval-harness/releases/tag/v1.0.0
