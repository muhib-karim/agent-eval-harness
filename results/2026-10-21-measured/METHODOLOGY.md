# Methodology: measured run, 21 October 2026

What was run, how, and what went wrong, written down as it happened. The numbers themselves are in
[`report.md`](report.md), [`report.html`](report.html) and [`summary.json`](summary.json);
every attempt's raw reply, extracted source and pytest log is under [`attempts/`](attempts/).

## Setup

| Item | Value |
| --- | --- |
| Date | 2026-10-21, 17:53:41Z to 18:11:34Z (one uninterrupted run; `--resume` was not needed) |
| Harness | agent-eval-harness 1.3.0, branch `upgrade/v1.3.0`; Python 3.11.16 on Linux |
| Config | [`examples/measured-2026-10-21.yaml`](../../examples/measured-2026-10-21.yaml) (SHA-256 in `metadata.json`) |
| Tasks | the 16 bundled tasks, 4 per category; spec, hidden-test and starter hashes in `metadata.json` match the committed files |
| Repeats | 3 per model and task, concurrency 4 |
| Attempts | 6 models × 16 tasks × 3 = 288 (budget: under about 350) |
| Sampling | each provider's default temperature (none sent), as in the 17 October run |
| Output budget | `max_tokens` 8192 for the Messages-API models, `max_completion_tokens` 16384 for gpt-6-sol |
| Request timeout | 240 s (Messages API), 300 s (gpt-6-sol); grading timeout is each task's `timeout_s` |
| Statistics | task-macro pass@1 and unbiased pass@3; 95% task-level percentile bootstrap, seed 20261021, 2000 resamples; paired bootstrap for overlapping intervals |

All six models were reached over HTTP through the harness's own runners: `anthropic` (Messages
API) for the Claude models and `openai` (Chat Completions) for gpt-6-sol. Endpoints and keys came
from environment variables named in the config; no URL, host or key is stored in this directory.
Usage is as reported by the endpoints. No endpoint reported cost, so cost is `unknown`
throughout; the harness does not estimate it.

## Model selection

The task called for at least four models: claude-opus-5-5, claude-sonnet-5, claude-haiku-4-5 and
gpt-6-sol, plus others only if they answered. Before the run, a one-message probe ("Reply with
OK.") was sent to candidate ids. claude-fable-5-1, claude-sonnet-5-5 and claude-haiku-5-5 also
answered. The first two were added; claude-haiku-5-5 was left out because a seventh model would
have brought the run to 336 attempts, too close to the budget. The 17 October run's deepseek-chat
and grok-4.3 were not available from this environment and are not part of this run.

The first probe returned HTTP 404 for every Messages-API model because the base URL variable
lacked the API version path that the runner expects; with the version path added, all answered.
Probes are not attempts and are not recorded in `results.jsonl`.

## Results in one table

| Model | pass@1 | 95% CI | pass@3 | Non-passing attempts (of 48) |
| --- | ---: | ---: | ---: | --- |
| claude-sonnet-5-5 | 100.0% | 100.0–100.0% | 100.0% | none |
| claude-opus-5-5 | 100.0% | 100.0–100.0% | 100.0% | none |
| claude-fable-5-1 | 100.0% | 100.0–100.0% | 100.0% | none |
| gpt-6-sol | 97.9% | 93.8–100.0% | 100.0% | 1 fail |
| claude-sonnet-5 | 79.2% | 60.4–93.8% | 87.5% | 6 fail, 4 error |
| claude-haiku-4-5 | 66.7% | 47.9–85.4% | 81.2% | 9 fail, 4 error, 3 timeout |

Paired comparisons (same seed): gpt-6-sol beats claude-sonnet-5 by +18.8 points (paired 95% CI
+4.2 to +37.5), and claude-sonnet-5 beats claude-haiku-4-5 by +12.5 points (+4.2 to +22.9). The
four models at or near 100% cannot be separated on this suite.

## Failures and DNFs, as they happened

27 of 288 attempts did not pass: 16 `fail`, 8 `error`, 3 `timeout`. None was retried; every one
is in the results as recorded.

**Ran out of output budget (claude-sonnet-5, 6 attempts).** Four attempts (`json_path` ×1,
`levenshtein` ×2, `undo_buffer` ×1) used the full 8192 output tokens and returned no text at all,
so they are recorded as `error: model returned empty code`. The response contained no text block
and the harness does not save the stop reason, but the reported output count equals the budget
in every case. Two more (`levenshtein`, `undo_buffer`) also hit 8192 tokens and were graded on
truncated code (14/17 and 1/18). The budget is the same as in the 17 October run and was not
raised for this model, so these count as failures of the protocol as configured.

**Reply format (claude-haiku-4-5, 4 attempts).** The prompt asks for the complete module in a
single Python code block. The harness joins all Python-labelled blocks, a documented rule meant
for models that split code across blocks. Four replies broke the single-block instruction:
`fix_memoize` and `fix_slugify` returned the full fixed module and then a second block quoting
the changed line; one `undo_buffer` reply put the filename in its own Python block; another
opened a fence twice. Each joined module fails at import (`NameError` or `SyntaxError`), so the
attempt is an `error`. In the first two cases the first block alone was a correct-looking fix.
The outcome stands as recorded. A stricter extraction rule for single-block prompts is on the
roadmap; changing it after seeing these results would be post-hoc.

**Grading timeouts (claude-haiku-4-5, `levenshtein` ×3).** Each solution passed the first 16
tests and then exceeded the task's 10-second limit on the 20,000-character case. The prompt
requires the `max_distance` bound to make that case fast; these solutions computed the full table.

**Substantive misses.**

- `arithmetic`: claude-sonnet-5 and claude-haiku-4-5 failed all three attempts, each on the same
  single test (30/31): the full-width digit `"２"` must be rejected, but `str.isdigit()` and
  `float()` accept it. This is the same failure the 17 October run found.
- `intervals`: three attempts (claude-sonnet-5 ×1, claude-haiku-4-5 ×2) failed the same case,
  merging integer-adjacent ranges that the spec keeps apart.
- `json_path`: claude-haiku-4-5 failed all three attempts (13–19/26), accepting malformed paths
  such as `a..b`, `a.` and `$name`. gpt-6-sol's only failure is one attempt here (25/26),
  accepting `$.[0]`.
- `semver`: one claude-haiku-4-5 attempt (25/27) accepted the numeric prerelease `01`.

## Scrubbing

The run was written to a scratch directory and copied here with machine-specific paths replaced:
the repository root by `./` in `config.resolved.yaml` and `metadata.json`, and one temporary
workdir path in a test log by `<workdir>`. After the copy, every file was checked for absolute
machine paths, endpoint hosts and credentials; none remained. Credentials are also redacted by
the harness at write time. The reports were then regenerated from `results.jsonl` with
`--k 1 --k 3`.

## Reproduce

```sh
pip install '.[grade]'
# ANTHROPIC_BASE_URL and OPENAI_BASE_URL must include the API version path; keys in the
# matching *_API_KEY variables.
agent-eval run examples/measured-2026-10-21.yaml --out runs/measured   # add --resume if interrupted
```

## Limits

Sixteen small single-module Python tasks, three repeats, one day, one output budget, default
temperatures. Four models saturate the suite, so it cannot rank them. Read this as a regression
baseline for these tasks and settings, not as a general ranking of the models.
