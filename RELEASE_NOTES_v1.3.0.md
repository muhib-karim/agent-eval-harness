# agent-eval-harness 1.3.0

Released 2026-10-21. Full list of changes: [CHANGELOG.md](CHANGELOG.md#130---2026-10-21).

1.3.0 turns the harness from a six-task demo into a small, maintained evaluation tool. It has 16
tasks in four categories, confidence intervals on every score, a self-contained accessible
report, presets for agent CLIs, resumable runs, stricter CI, and a second measured run on the
new suite.

## Highlights

- **16 tasks, four categories.** `algorithms`, `parsing`, `stateful` and `bug-fix`, four tasks
  each, 279 hidden tests in total. Bug-fix tasks hand the model a buggy module and an issue report
  (new `starter` field). CI proves that every task is solvable, that no hidden test passes on an
  empty module or a `None`-returning stub, and that every buggy starter fails some tests while
  passing others.
- **Scores with error bars.** pass@1 now comes with a seeded task-level bootstrap 95% interval
  (seed 20261021, 2000 resamples). Models whose intervals overlap get a paired bootstrap
  comparison, and pass@1 is broken down by category.
- **A report you can hand to someone.** The HTML report is one file with no external assets. It
  has a leaderboard sortable from the keyboard (a plain table without JavaScript), interval
  charts, a category heatmap that prints the number in every cell, explicit `unknown` usage, dark
  mode and a 375 px layout.
- **Agent CLIs as first-class runners.** `cli` presets for `claude-code`, `codex` and `opencode`,
  with an environment allow-list, optional private `HOME`, and token and cost parsing from Claude
  Code's JSON output.
- **Resumable runs.** `agent-eval run CONFIG --out DIR --resume` finishes an interrupted run
  without re-running or discarding recorded attempts.
- **CI quality gates.** ruff lint and format, strict mypy, an 85% coverage gate on Python 3.11 and
  3.12, a gitleaks job, CodeQL and Dependabot.

## Measured results (21 October 2026)

Six models, the 16 tasks, three repeats: 288 live attempts through the harness's HTTP runners,
each graded against withheld tests. The evidence for every attempt is in
[`results/2026-10-21-measured/`](results/2026-10-21-measured/). Settings and every failure are
in [METHODOLOGY.md](results/2026-10-21-measured/METHODOLOGY.md).

| Model (id, 21 Oct 2026) | pass@1 | 95% CI | pass@3 |
| --- | ---: | ---: | ---: |
| claude-sonnet-5-5 | 100.0% | 100.0–100.0% | 100.0% |
| claude-opus-5-5 | 100.0% | 100.0–100.0% | 100.0% |
| claude-fable-5-1 | 100.0% | 100.0–100.0% | 100.0% |
| gpt-6-sol | 97.9% | 93.8–100.0% | 100.0% |
| claude-sonnet-5 | 79.2% | 60.4–93.8% | 87.5% |
| claude-haiku-4-5 | 66.7% | 47.9–85.4% | 81.2% |

Caveats, stated plainly:

- **The suite does not separate the top four.** Their paired differences all include zero. Ranking
  them needs harder tasks.
- **27 of 288 attempts did not pass, and none was retried.** Six claude-sonnet-5 attempts used
  the whole 8,192-token output budget; four of them returned no text. The budget was not raised
  after the fact. Four claude-haiku-4-5 errors are reply-format errors: a second code block or a
  doubled fence, combined with the documented rule that joins all Python blocks. They stand as
  recorded.
- **Not comparable with the 17 October run.** That run used six tasks, not 16, and included two
  models (deepseek-chat, grok-4.3) that were not available this time. It stays published as
  history.
- **Small, public tasks.** Sixteen single-module Python tasks, three repeats, one day, default
  temperatures. Read the run as a regression baseline for these tasks and settings, not as a
  general model ranking. Cost is `unknown` because no endpoint reported it.

## Upgrade notes

- **Behaviour change: agent CLIs no longer inherit your whole environment.** A `cli` runner now
  passes only `PATH`, `HOME`, `LANG`, `LC_ALL`, `TERM`, `TMPDIR`, `USER` and `SYSTEMROOT`, the
  selected preset's credential variables, and any names you list in the new `env_passthrough`
  option. If your agent command relied on another variable (an API key, a proxy setting, a config
  path), add its name:

  ```yaml
  - name: my-agent
    runner: cli
    options:
      command: [my-agent, --prompt-file, '{prompt_file}']
      env_passthrough: [MY_AGENT_API_KEY, HTTPS_PROXY]
  ```

  Values of forwarded variables that are 8 characters or longer are redacted from saved artifacts.
- **Results files:** each JSONL line may carry a new optional `category`. The change is additive,
  `schema_version` stays `"1.0"`, and 1.2.0 result files still load (as `uncategorized`).
- **Summary JSON:** `summary.json` and `report --format json` gain fields (`pass_at_1_ci`,
  `categories`, `task_categories`, `bootstrap`, `comparisons`). Existing fields are unchanged.
- **Task authors:** reference solutions no longer need to live in the task directory. Keep them
  elsewhere and check them with `agent-eval validate-task TASK --reference FILE`. An in-directory
  `reference.py` still works. Add `category:` to your `task.yaml` to get per-category scores.
- **Mock runner:** the bundled demo now reads solutions through `reference_dir`. Custom configs
  using `fixtures` or an in-task `reference.py` keep working.

## Install

```sh
pip install "agent-eval-harness[grade] @ https://github.com/muhib-karim/agent-eval-harness/releases/download/v1.3.0/agent_eval_harness-1.3.0-py3-none-any.whl"
```

The `grade` extra installs pytest, which grading needs. Check the wheel against
`SHA256SUMS.txt` on the release page. To run the offline demo, use a checkout:

```sh
git clone https://github.com/muhib-karim/agent-eval-harness && cd agent-eval-harness
pip install '.[grade]' && agent-eval run examples/mock-demo.yaml --out runs/demo
```
