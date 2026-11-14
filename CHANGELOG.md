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
  by name only. Each command runs as `docker create` followed, once that has finished, by
  `docker start --attach`; the container is then always removed with `docker rm --force`, in a
  cleanup that cancellation cannot interrupt and that is retried briefly on failure. Containers
  carry `agent-eval.attempt=<name>` and per-run `agent-eval.run=<run id>` labels; at the end of
  every run with docker isolation (also after an error or Ctrl-C) the harness removes any container still
  labelled with the run's id, such as one whose interrupted `create` the daemon completed, and
  warns with the count. A container that cannot be removed is
  noted in the attempt's output and on stderr; one the daemon creates after the sweep can be found
  with `docker ps -a --filter label=agent-eval.run`. Grading uses the image's `python`,
  which needs pytest (the default `python:3.12-slim` does not have it; the harness image does).
- If docker isolation is requested but docker is missing or its daemon is unreachable, the run
  stops with exit code 2 before anything is generated or written: isolation is asked for to
  contain untrusted code, so it is not silently replaced by running that code on the host.
  `agent-eval run --allow-local-fallback` (or `isolation: {fallback: local}`) opts into the local
  runner instead; the run then prints one warning and records it on every attempt. The permission
  is not stored in `config.resolved.yaml`, so a resume may add or drop it.
- A pytest preflight: before anything is generated, the run checks that the grading interpreter
  (the host's `python -I`, or the image's `python` with docker isolation) can import pytest, and
  stops with exit code 2 if not. Previously a missing `grade` extra, pytest installed only in the
  user site, or the default `python:3.12-slim` image turned every attempt into an `error` after
  its generation had been paid for, and the run still exited 0.
- `metadata.json` of a resumed run gains a `resumes` list: each resume's time, config hash,
  harness and Python versions and platform. The top-level fields keep describing the first
  invocation.
- `tests/test_committed_results.py` checks the measured runs under `results/`: every recorded
  attempt has its evidence, and the newest run's task hashes and config hash still match the tree.
- Retry with backoff for transient provider errors in the `openai` and `anthropic` runners: HTTP
  408, 409, 425, 429, 500, 502, 503, 504, 529 and connection errors are retried with full-jitter
  exponential backoff (3 retries, 1 s base, ×2, 30 s cap by default). A `Retry-After` header in
  seconds is honoured up to the cap. Other 4xx, invalid responses and the `timeout_s` deadline
  are not retried, and neither are the `cli` (an agent may have changed the workdir) and `mock`
  runners. Configure with a top-level `retry:` block, a per-model `retry` runner option, or
  `agent-eval run --max-retries N`. `timeout_s` bounds the whole generation, including every
  retry and backoff wait.
- Isolation `memory` must be at least `6m` (docker's minimum), counted in whole bytes the way docker
  does: `0` (docker's "no limit") and values such as `0.5b`, which docker truncates to 0, are rejected.
- A per-model `isolation` list in the `summary.json` of reports (`requested`, `used`,
  `attempts`), counting how many attempts asked for one isolation mode and ran under another.
  Attempts recorded before isolation existed are not counted, so an older run has an empty
  list. When any attempts were downgraded (docker requested, run on the host), `report.html` and
  the Markdown report gain a note naming each model and how many of its attempts ran with the
  local runner.
- `agent-eval compare-context FULL TRIMMED`: an offline paired comparison of two saved result
  files (trimmed minus full pass@1 with a paired task-level bootstrap interval, wall-time and
  reported-token differences), written as JSON. It makes no model calls. See
  [docs/context-engineering.md](docs/context-engineering.md).

### Changed

- The results JSONL gains an optional `isolation` field (`requested`, `used`, `warning`). The
  change is additive: older result files still load, resume and report, and `schema_version`
  stays `"1.0"`.
- The results JSONL gains `retries` and `retry_reasons` (e.g. `["http_429", "http_503"]`) on every
  attempt, including attempts that failed after exhausting their retries. Reports show a retries
  total per model. Older files without these fields load with `0` and `[]`, resume and report.
- `fallback: local` with `network: bridge` now needs `--force` (keyword-only `force` on
  `run_config`). When docker is unavailable, the run no longer falls back to the host for a
  config whose attempts are expected to be networked: it exits with code 2 unless `--force` is
  passed. Without `network: bridge` the fallback is unchanged.
- `config.resolved.yaml` records the effective isolation mode, including an `--isolation`
  override, and `--resume` refuses a run whose mode differs (a run without the entry counts as
  `local`).
- `config.resolved.yaml` records a `--max-retries` override as `max_retries_override`, and
  `--resume` refuses a run whose override differs (a run without the entry had none).
- `main` now carries a development version, `1.4.0.dev0`, and the version is written in one
  place (`src/agent_eval/__init__.py`; the build reads it). Every run records it in
  `metadata.json`, where code past the 1.3.0 tag was still stamped `1.3.0`.
- Dependency floors: pydantic 2.14.2, pytest 9.2.0 (also for the `grade` extra), mypy 2.4.1,
  ruff 0.17.3, types-PyYAML 6.0.12.20261030, hatchling 1.33.0. No upper bound changed.
- The coverage gate is 95% (was 85%) and warnings raised during the tests are errors.
- The sdist no longer ships `results/`, `docs/assets/` and `.github/` (770 KB to 140 KB).
- CI: Python 3.13 and 3.14 join the matrix; a `pip-audit` job; both demo jobs assert the pass
  rates instead of trusting the exit code; pushes run on `main` only, plus pull requests, a
  weekly schedule and manual dispatch.

### Fixed

- `--resume` no longer corrupts `results.jsonl` when the interrupted run lost only the final
  newline: the next record used to be appended to the same line, the resume exited 0, and the
  file could no longer be loaded. A half-written final line is now truncated in place instead of
  rewriting the whole file.
- A workdir that cannot be removed (for example because a detached child of an agent is still
  writing into it) no longer aborts the whole run or loses the attempt; the attempt keeps its
  outcome and a warning names the directory. The same holds for the hidden-test directory.
- Pass@1 is exact. It went through the log form used for pass@k, so 1/3 became
  0.33333333333333337; models with equal pass rates could then rank in the wrong order instead
  of by wall time, and a point estimate could fall outside its own interval.
- Resuming a run whose `config.resolved.yaml` or `metadata.json` is empty or not a mapping is
  reported as a damaged run (exit code 2) instead of a traceback.
- A cancellation that arrives while a command's output pipe is being connected now kills the
  command; it used to be left running.
- README: the 17 October run's recorded harness version (1.1.0), what `--resume` compares, and
  which sections describe unreleased features.

### Security

- The Markdown report escapes Markdown syntax in model, task and category labels, so a label
  such as `[text](url)` or `![](url)` from a config or from someone else's `results.jsonl` is
  shown as text rather than rendered as a link or a remote image. The HTML report was already
  safe.
- Workflows pin every action to a commit SHA, check out without persisting the token (including
  the release job, whose token can write releases), and the Pages build job no longer holds the
  deploy permissions. gitleaks is verified against its SHA-256 before it runs.
- The Dockerfile's base image is pinned by digest and kept current by Dependabot.
- The release workflow checks for the exact wheel filename, so a development build such as
  `1.4.0.dev0` cannot be published under the tag `v1.4.0`.

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
