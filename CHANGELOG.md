# Changelog

All notable changes are recorded here. Versions follow [Semantic Versioning](https://semver.org/).

## 1.2.0 — 2026-10-18

- First measured live-model run: six models, six tasks, three repeats (108 attempts), committed
  with every attempt's evidence under `results/2026-10-17-measured/` and summarised in the README.
- HTTP runner option `token_param` (`max_tokens` or `max_completion_tokens`) for OpenAI-compatible
  models that reject `max_tokens`.
- The GitHub Pages site now leads with the measured report; the offline mock demo moved to `/demo/`.
- `CITATION.cff`.

## 1.1.0 — 2026-10-03

- Result loading rejects impossible records: `tests_passed` greater than `tests_total`, and
  duplicate model/task/repeat samples that would inflate pass@k.
- New tests for both checks.
- CI publishes the offline demo's HTML report to GitHub Pages on every push to `main`.
- Package metadata: author and project URLs.

## 1.0.0 — 2026-09-29

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
