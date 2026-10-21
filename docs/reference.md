# Reference

- [Run config](#run-config)
- [Runners](#runners)
- [Writing a task](#writing-a-task)
- [Run directory and JSONL schema](#run-directory-and-jsonl-schema)
- [Outcomes and scoring](#outcomes-and-scoring)
- [CLI exit codes](#cli-exit-codes)
- [Library use and custom runners](#library-use-and-custom-runners)

## Run config

```yaml
models:
  - name: local-reference
    runner: mock
    options:
      variant: reference
tasks:
  - ../tasks/*/task.yaml
repeats: 2
concurrency: 2
```

| Field | Meaning |
| --- | --- |
| `models` | Nonempty list of `name`, registered `runner`, and runner-specific `options`. Names must be unique. |
| `tasks` | Nonempty list of task YAML globs, resolved relative to the config file. `**` is supported. Every glob must match; duplicate matches are merged; task ids must be unique. |
| `repeats` | Attempts per model × task. Default 1. |
| `concurrency` | Maximum simultaneous attempts (generation plus grading). Default 1. |

Unknown fields in the config and in built-in runner options are rejected.

## Runners

| Runner | Options |
| --- | --- |
| `openai` | Chat Completions-compatible endpoint. Required `model`, `base_url_env`, `api_key_env`; optional `max_tokens` (4096), `token_param` (`max_tokens` or `max_completion_tokens`; default `max_tokens`), `timeout_s` (120), `temperature` (omitted unless set). |
| `anthropic` | Messages API endpoint, version header `2023-06-01`. Same options. |
| `cli` | Either `preset` (`claude-code`, `codex`, `opencode`) or `command` (argv list or shell-like string). Optional `timeout_s` (120, or 600 for presets), `env_passthrough`, `isolate_home`; presets also take `executable`, `model`, `extra_args`. |
| `mock` | `variant`: `reference` (default) or `wrong`; optional `fixtures`: task id → task-relative Python file; optional `reference_dir`: directory of `<task_id>.py` solutions, relative to the config. |

### HTTP runners

`base_url_env` and `api_key_env` name environment variables; literal URLs and keys never go in
the config. The base URL must include the API version path; the runner appends
`/chat/completions` or `/messages`. Requests are non-streaming and `timeout_s` is a total
wall-clock deadline, not a per-read timeout. Redirects are not followed.

The prompt asks for one Python code block. `extract_code` in `runners/base.py` takes Python-labelled
fences first, then unlabelled fences, and tolerates a missing closing fence.

Token counts come from the response's `usage` object. Cost is recorded only if the response
includes `usage.cost_usd`; there is no pricing table. On HTTP errors the recorded error is the
status code only. Response bodies, headers and URLs are not saved.

See [`examples/real-models.yaml`](../examples/real-models.yaml) for a two-endpoint config.

### CLI runner

Arguments support the `{prompt}`, `{prompt_file}`, `{workdir}` and `{entrypoint}` placeholders;
write literal braces as `{{` and `}}`. `{prompt}` is the whole prompt as one argument. No shell
is launched, so pipes, redirection and `VAR=value` prefixes are passed through literally. Prefer
the argv-list form:

```yaml
models:
  - name: external-agent
    runner: cli
    options:
      command: [agent-command, --prompt-file, '{prompt_file}', --output, '{entrypoint}']
      timeout_s: 180
tasks: [../tasks/*/task.yaml]
```

The command runs with the fresh workdir as its cwd and must write the entrypoint file itself
(for bug-fix tasks the buggy starter is already there). Its stdout/stderr are saved as
`model-output.txt` but not treated as code. stdin is `/dev/null`. A non-zero exit is recorded
as an `error` attempt. On POSIX, anything left in the command's process group is killed when it
exits or times out.

**Environment allow-list.** The agent receives only `PATH`, `HOME`, `LANG`, `LC_ALL`, `TERM`,
`TMPDIR`, `USER` and `SYSTEMROOT`, plus the preset's credential variables and any names in
`env_passthrough`. Everything else in the parent environment is withheld. Values of forwarded
variables that are at least 8 characters long are redacted from saved artifacts. (Before 1.3.0
the command inherited the whole parent environment; add what your agent needs to
`env_passthrough`.)

**Workdir isolation.** Each attempt runs in its own temporary directory that holds only the
prompt file and, for bug-fix tasks, the starter; hidden tests are copied in only after the agent
exits. `isolate_home: true` also points `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`,
`XDG_DATA_HOME` and `TMPDIR` at a fresh empty directory outside the workdir, deleted afterwards,
so the agent cannot read host configuration, history or other projects. Agents that keep their
login under `HOME` then need an API key passed through the environment instead.

#### Agent CLI presets

| Preset | Command template | Forwarded credentials | Usage |
| --- | --- | --- | --- |
| `claude-code` | `claude -p {prompt} --output-format json --permission-mode acceptEdits --allowedTools Read,Edit,Write` | `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_BASE_URL` | tokens and cost from the JSON result |
| `codex` | `codex exec --full-auto --skip-git-repo-check --cd {workdir} {prompt}` | `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `CODEX_HOME` | unknown |
| `opencode` | `opencode run {prompt}` | `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `OPENCODE_CONFIG` | unknown |

`model` appends `--model <id>`; `extra_args` are appended after the template and may use the
placeholders; `executable` replaces the binary name (e.g. a pinned install path). Preset
timeouts default to 600 seconds. The flags follow each CLI's documented non-interactive mode as
of October 2026 and are covered in CI only by a fake CLI (`tests/test_cli_presets.py`), not by
the real tools. If a CLI changes its flags, override with `extra_args` or switch to `command`.
See [`examples/agent-clis.yaml`](../examples/agent-clis.yaml).

### Mock runner

`reference` copies a known-good solution to the entrypoint: the file named in `fixtures`, else
`<reference_dir>/<task_id>.py`, else the task's own `reference.py`. The bundled demo uses
`reference_dir: ../tests/fixtures/reference`.
`wrong` writes a module whose `__getattr__` returns a function that returns `None` for every name.
It exists to exercise the harness offline. It says nothing about any model.

## Writing a task

A task is a directory with `task.yaml` and one or more pytest files. Keep the reference
solution outside the shipped task directory (the bundled tasks keep theirs in
`tests/fixtures/reference/<task_id>.py`) so nothing answer-bearing ships next to the prompt:

```yaml
id: answer
title: Return an answer
prompt: Implement answer() returning the integer 42.
language: python
entrypoint: solution.py
hidden_tests: [hidden_tests.py]
category: algorithms
timeout_s: 5
tags: [intro, functions]
```

Defaults: `reference: reference.py` (used only if present), `language: python` (the only
supported value), `timeout_s: 10`, `tags: []`, `category` unset (reported as
`uncategorized`; lowercase letters, digits, `-` and `_`), `starter` unset.

**Bug-fix tasks** set `starter: starter.py`: the engine copies that file to the entrypoint
before generation. HTTP runners embed its source in the prompt and ask for the complete fixed
module; CLI agents find it in their workdir. Write the issue report (symptom and reproduction)
as the prompt, and hidden tests that catch the bug plus regression tests that the buggy
starter already passes. `entrypoint` must be a plain module filename and may not shadow
`conftest.py`, `pytest.py`, `sitecustomize.py` or `usercustomize.py`. Test and reference paths
must resolve inside the task directory, including through symlinks.

```python
# tests/fixtures/reference/answer.py (outside the task directory)
def answer() -> int:
    return 42
```

```python
# hidden_tests.py
from solution import answer


def test_answer() -> None:
    assert answer() == 42
```

Check it with `agent-eval validate-task path/to/task.yaml --reference path/to/answer.py`, which
grades the solution exactly as a generated one would be graded (omit `--reference` to use a
`reference.py` inside the task directory). For the bundled suite, `tests/test_task_suite.py`
also checks that no hidden test passes on an empty module or on a stub whose every call
returns `None`, and that each bug-fix starter fails some hidden tests and passes others.

Constraints to design around:

- Only the listed test files are copied, renamed to `test_000.py`, `test_001.py`, and so on. A
  shared `conftest.py`, data files and third-party pytest plugins are not available.
- Solutions and tests should need only the standard library.
- Put every error type and boundary rule the tests check into the prompt. The tests should
  check the stated contract, not requirements the prompt never mentions.

## Run directory and JSONL schema

```text
config.resolved.yaml          # config with task globs expanded to absolute paths
metadata.json                 # harness/Python versions, platform, start time, SHA-256 hashes
results.jsonl                 # one object per completed attempt, schema_version "1.0"
summary.json                  # same data as `agent-eval report --format json`
report.html
attempts/attempt-000001/
    model-output.txt          # model reply, or CLI stdout+stderr
    solution.py               # generated entrypoint, if one was written
    test.log                  # pytest stdout+stderr
```

`metadata.json` hashes the config, each task spec, its hidden tests, its starter and reference
(if present), and any mock fixtures or `reference_dir` solutions in use. A resumed run adds a
`resumed_at` list of timestamps.

Each JSONL line has: `attempt_id`, `model`, `runner`, `task_id`, `repeat`, `outcome`,
`tests_passed`, `tests_total`, `wall_time_s`, `generation_time_s`, `grading_time_s`,
`input_tokens`, `output_tokens`, `cost_usd` (the last three nullable), `error`, and `artifacts`
(path relative to the run directory), plus the optional `category` (added in 1.3.0; older files
without it load as `uncategorized`, and `schema_version` stays `"1.0"`). Lines are appended and flushed as attempts complete, so
the file is in completion order. Attempt ids follow scheduling order and are deterministic for a
given config.

Every configured `api_key_env` value present in the environment, and every value of 8 or more
characters forwarded to a CLI agent, is replaced with `[REDACTED]` in all saved text. This is exact string matching on known keys, not a general secret scanner.

Output directories must not already exist. The harness never overwrites a previous run.

`agent-eval run CONFIG --out DIR --resume` continues an interrupted run in `DIR`. It refuses to
start unless the resolved config and every task hash match the original run. It keeps every
recorded attempt, including errors, so a resumed run never retries a failure away. It drops a
half-written final JSONL line, replaces leftover artifacts of unrecorded attempts, and runs only
the missing model/task/repeat combinations under their original attempt ids. With `--resume` and
no existing `DIR`, it starts a fresh run.

## Outcomes and scoring

| Outcome | Meaning |
| --- | --- |
| `pass` | pytest exited 0, at least one test ran, and every test case passed |
| `fail` | At least one failure, or skipped cases, so the suite did not fully pass |
| `error` | Generation failed, the entrypoint is missing, collection/setup error, or pytest crashed or produced no XML |
| `timeout` | Generation or grading exceeded its timeout; test counts are zero |

`tests_total` counts JUnit XML test cases, including skipped ones and collection errors. It is
not a count of assertions.

Pass@1 for a task is c/n over its attempts. Pass@k uses the unbiased estimator

```text
pass@k = 1 - C(n-c, k) / C(n, k),   1 <= k <= n
```

Both are averaged over tasks with equal weight (macro average). By default `report` shows
k ∈ {1, 2, 5, 10}, limited to values where every task for that model has at least k
attempts; pass `--k` one or more times to choose others. The estimator assumes attempts are
independent samples. That holds approximately for sampled API calls at nonzero temperature. It
does not hold for deterministic fixtures, or for agent sessions that share state.

**Confidence intervals.** Each model's pass@1 gets a 95% task-level percentile bootstrap
interval: tasks are drawn with replacement (repeats of a task stay together, because they are
correlated), the per-task pass rates of each draw are averaged, and the interval is the 2.5th to
97.5th percentile of 2000 such means. The seed (default 20261021) and resample count are fixed
and recorded in every summary; change them with `report --seed` and `--resamples`. The
interval reflects uncertainty about which tasks were sampled, not run-to-run noise on a fixed
task.

**Paired comparisons.** For every pair of models whose intervals overlap, the report bootstraps
the mean per-task difference over the tasks both models ran, using the same seed. If that
interval excludes zero, the models differ on this suite even though their marginal intervals
overlap. Pairing removes the between-task variance that two separate intervals count twice.

**Categories.** Pass@1 is also averaged within each task `category`; tasks without one are
`uncategorized`.

If models were run on different task sets, their averages cover different tasks. The per-task
matrix shows `—` for missing cells.

Wall time covers generation plus grading and excludes time spent waiting for a concurrency slot.
With `concurrency > 1`, attempts compete for CPU, so it is not a clean latency measurement.

## CLI exit codes

| Code | When |
| --- | --- |
| 0 | Command completed. A `run` exits 0 even if every attempt failed. |
| 1 | `validate-task`: the reference did not pass |
| 2 | Invalid config, task, results file or arguments; I/O error |
| 130 | Interrupted. Lines already in `results.jsonl` remain valid. |

## Library use and custom runners

```python
import asyncio
from pathlib import Path

from agent_eval.engine import run_config
from agent_eval.report import render_report
from agent_eval.results import summarize

attempts = asyncio.run(run_config(Path("examples/mock-demo.yaml"), Path("runs/library-demo")))
markdown = render_report(summarize(attempts), "md")
```

A runner implements the `agent_eval.runners.base.Runner` protocol:

```python
async def generate(self, task: TaskSpec, workdir: Path) -> Generation: ...
```

It writes `task.entrypoint` into `workdir` and returns a `Generation` with the raw output and any
token and cost figures the endpoint reported. On failure it raises `RunnerError`. The message is
saved as-is, so it must not contain secrets. Runners are responsible for their own deadline and
must handle cancellation.

Register a factory before calling `run_config`:

```python
from agent_eval.runners import register_runner

register_runner("my-runner", lambda options, *, task_path: MyRunner(options))
```

The factory receives the model's `options` dict unvalidated. It is called once per attempt
before anything runs, so bad options fail the whole run up front. The registry is per-process.
The `agent-eval` CLI has only the four built-in runners.
