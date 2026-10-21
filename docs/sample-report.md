# Coding task comparison

64 attempts. Pass rates are task-macro-averaged. Missing usage is unknown.

95% CI: task-level percentile bootstrap, 2000 resamples, seed 20261021.

| Model | Pass@1 | 95% CI | Pass@k | Mean (s) | Median (s) | Input / output tokens | Cost (USD) |
| --- | ---: | ---: | --- | ---: | ---: | --- | --- |
| mock-reference | 100.0% | 100.0%–100.0% | 1: 100.0%, 2: 100.0% | 1.168 | 1.011 | unknown / unknown | unknown |
| mock-wrong | 0.0% | 0.0%–0.0% | 1: 0.0%, 2: 0.0% | 1.095 | 1.076 | unknown / unknown | unknown |

## Per-task passes / attempts

| Task | mock-reference | mock-wrong |
| --- | ---: | ---: |
| arithmetic | 2/2 | 0/2 |
| fix_binary_search | 2/2 | 0/2 |
| fix_memoize | 2/2 | 0/2 |
| fix_running_stats | 2/2 | 0/2 |
| fix_slugify | 2/2 | 0/2 |
| ini_parser | 2/2 | 0/2 |
| intervals | 2/2 | 0/2 |
| json_path | 2/2 | 0/2 |
| ledger | 2/2 | 0/2 |
| levenshtein | 2/2 | 0/2 |
| lru_ttl | 2/2 | 0/2 |
| rate_limiter | 2/2 | 0/2 |
| roman | 2/2 | 0/2 |
| semver | 2/2 | 0/2 |
| topo_sort | 2/2 | 0/2 |
| undo_buffer | 2/2 | 0/2 |

## Pass@1 by category

| Category | Tasks | mock-reference | mock-wrong |
| --- | ---: | ---: | ---: |
| algorithms | 4 | 100.0% | 0.0% |
| bug-fix | 4 | 100.0% | 0.0% |
| parsing | 4 | 100.0% | 0.0% |
| stateful | 4 | 100.0% | 0.0% |

Reported totals may be partial. Usage coverage (attempts with input/output/cost):

- mock-reference: 0/0/0 of 32.
- mock-wrong: 0/0/0 of 32.
