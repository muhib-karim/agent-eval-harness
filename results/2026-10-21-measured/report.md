# Coding task comparison

288 attempts. Pass rates are task-macro-averaged. Missing usage is unknown.

95% CI: task-level percentile bootstrap, 2000 resamples, seed 20261021.

| Model | Pass@1 | 95% CI | Pass@k | Mean (s) | Median (s) | Input / output tokens | Cost (USD) |
| --- | ---: | ---: | --- | ---: | ---: | --- | --- |
| claude-sonnet-5-5 | 100.0% | 100.0%–100.0% | 1: 100.0%, 3: 100.0% | 9.422 | 8.814 | 20727 / 55573 | unknown |
| claude-opus-5-5 | 100.0% | 100.0%–100.0% | 1: 100.0%, 3: 100.0% | 12.917 | 11.890 | 20727 / 62037 | unknown |
| claude-fable-5-1 | 100.0% | 100.0%–100.0% | 1: 100.0%, 3: 100.0% | 18.695 | 17.116 | 20727 / 74638 | unknown |
| gpt-6-sol | 97.9% | 93.8%–100.0% | 1: 97.9%, 3: 100.0% | 11.281 | 10.064 | 13755 / 38837 | unknown |
| claude-sonnet-5 | 79.2% | 60.4%–93.8% | 1: 79.2%, 3: 87.5% | 27.583 | 14.907 | 20631 / 129892 | unknown |
| claude-haiku-4-5 | 66.7% | 47.9%–85.4% | 1: 66.7%, 3: 81.2% | 9.028 | 8.838 | 15678 / 43707 | unknown |

## Per-task passes / attempts

| Task | claude-sonnet-5-5 | claude-opus-5-5 | claude-fable-5-1 | gpt-6-sol | claude-sonnet-5 | claude-haiku-4-5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| arithmetic | 3/3 | 3/3 | 3/3 | 3/3 | 0/3 | 0/3 |
| fix_binary_search | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| fix_memoize | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 2/3 |
| fix_running_stats | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| fix_slugify | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 2/3 |
| ini_parser | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| intervals | 3/3 | 3/3 | 3/3 | 3/3 | 2/3 | 1/3 |
| json_path | 3/3 | 3/3 | 3/3 | 2/3 | 2/3 | 0/3 |
| ledger | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| levenshtein | 3/3 | 3/3 | 3/3 | 3/3 | 0/3 | 0/3 |
| lru_ttl | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| rate_limiter | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| roman | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| semver | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 2/3 |
| topo_sort | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| undo_buffer | 3/3 | 3/3 | 3/3 | 3/3 | 1/3 | 1/3 |

## Pass@1 by category

| Category | Tasks | claude-sonnet-5-5 | claude-opus-5-5 | claude-fable-5-1 | gpt-6-sol | claude-sonnet-5 | claude-haiku-4-5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| algorithms | 4 | 100.0% | 100.0% | 100.0% | 100.0% | 66.7% | 58.3% |
| bug-fix | 4 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 83.3% |
| parsing | 4 | 100.0% | 100.0% | 100.0% | 91.7% | 66.7% | 41.7% |
| stateful | 4 | 100.0% | 100.0% | 100.0% | 100.0% | 83.3% | 83.3% |

## Paired comparisons where intervals overlap

- claude-sonnet-5-5 − claude-opus-5-5: +0.0% (paired 95% CI +0.0% to +0.0%). Intervals overlap and the paired 95% interval for the difference includes zero: no reliable difference between claude-sonnet-5-5 and claude-opus-5-5 on these 16 tasks.
- claude-sonnet-5-5 − claude-fable-5-1: +0.0% (paired 95% CI +0.0% to +0.0%). Intervals overlap and the paired 95% interval for the difference includes zero: no reliable difference between claude-sonnet-5-5 and claude-fable-5-1 on these 16 tasks.
- claude-sonnet-5-5 − gpt-6-sol: +2.1% (paired 95% CI +0.0% to +6.2%). Intervals overlap and the paired 95% interval for the difference includes zero: no reliable difference between claude-sonnet-5-5 and gpt-6-sol on these 16 tasks.
- claude-opus-5-5 − claude-fable-5-1: +0.0% (paired 95% CI +0.0% to +0.0%). Intervals overlap and the paired 95% interval for the difference includes zero: no reliable difference between claude-opus-5-5 and claude-fable-5-1 on these 16 tasks.
- claude-opus-5-5 − gpt-6-sol: +2.1% (paired 95% CI +0.0% to +6.2%). Intervals overlap and the paired 95% interval for the difference includes zero: no reliable difference between claude-opus-5-5 and gpt-6-sol on these 16 tasks.
- claude-fable-5-1 − gpt-6-sol: +2.1% (paired 95% CI +0.0% to +6.2%). Intervals overlap and the paired 95% interval for the difference includes zero: no reliable difference between claude-fable-5-1 and gpt-6-sol on these 16 tasks.
- gpt-6-sol − claude-sonnet-5: +18.8% (paired 95% CI +4.2% to +37.5%). Intervals overlap, but the paired 95% interval for the difference excludes zero: gpt-6-sol differs from claude-sonnet-5.
- claude-sonnet-5 − claude-haiku-4-5: +12.5% (paired 95% CI +4.2% to +22.9%). Intervals overlap, but the paired 95% interval for the difference excludes zero: claude-sonnet-5 differs from claude-haiku-4-5.

Reported totals may be partial. Usage coverage (attempts with input/output/cost):

- claude-sonnet-5-5: 48/48/0 of 48.
- claude-opus-5-5: 48/48/0 of 48.
- claude-fable-5-1: 48/48/0 of 48.
- gpt-6-sol: 48/48/0 of 48.
- claude-sonnet-5: 48/48/0 of 48.
- claude-haiku-4-5: 48/48/0 of 48.
