# Coding task comparison

108 attempts. Pass rates are task-macro-averaged. Missing usage is unknown.

| Model | Pass@1 | Pass@k | Mean (s) | Median (s) | Input / output tokens | Cost (USD) |
| --- | ---: | --- | ---: | ---: | --- | --- |
| gpt-6-sol | 100.0% | 1: 100.0%, 3: 100.0% | 11.009 | 10.600 | 2991 / 15301 | unknown |
| claude-opus-5-5 | 100.0% | 1: 100.0%, 3: 100.0% | 13.596 | 13.536 | 4947 / 22204 | unknown |
| claude-sonnet-5 | 72.2% | 1: 72.2%, 3: 83.3% | 28.350 | 20.262 | 4911 / 50167 | unknown |
| deepseek-chat | 61.1% | 1: 61.1%, 3: 66.7% | 5.540 | 5.221 | 3045 / 11789 | unknown |
| grok-4.3 | 50.0% | 1: 50.0%, 3: 50.0% | 15.348 | 14.886 | 6291 / 7328 | unknown |
| claude-haiku-4-5 | 44.4% | 1: 44.4%, 3: 66.7% | 10.394 | 10.692 | 3480 / 16681 | unknown |

## Per-task passes / attempts

| Task | gpt-6-sol | claude-opus-5-5 | claude-sonnet-5 | deepseek-chat | grok-4.3 | claude-haiku-4-5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| arithmetic | 3/3 | 3/3 | 0/3 | 0/3 | 0/3 | 0/3 |
| intervals | 3/3 | 3/3 | 1/3 | 2/3 | 0/3 | 1/3 |
| json_path | 3/3 | 3/3 | 3/3 | 0/3 | 0/3 | 0/3 |
| lru_ttl | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 1/3 |
| rate_limiter | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| roman | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |

Reported totals may be partial. Usage coverage (attempts with input/output/cost):

- gpt-6-sol: 18/18/0 of 18.
- claude-opus-5-5: 18/18/0 of 18.
- claude-sonnet-5: 18/18/0 of 18.
- deepseek-chat: 18/18/0 of 18.
- grok-4.3: 18/18/0 of 18.
- claude-haiku-4-5: 18/18/0 of 18.
