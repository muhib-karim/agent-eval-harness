# Coding task comparison

108 attempts. Pass rates are task-macro-averaged. Missing usage is unknown.

95% CI: task-level percentile bootstrap, 2000 resamples, seed 20261021.

| Model | Pass@1 | 95% CI | Pass@k | Mean (s) | Median (s) | Input / output tokens | Cost (USD) |
| --- | ---: | ---: | --- | ---: | ---: | --- | --- |
| gpt-6-sol | 100.0% | 100.0%–100.0% | 1: 100.0%, 3: 100.0% | 11.009 | 10.600 | 2991 / 15301 | unknown |
| claude-opus-5-5 | 100.0% | 100.0%–100.0% | 1: 100.0%, 3: 100.0% | 13.596 | 13.536 | 4947 / 22204 | unknown |
| claude-sonnet-5 | 72.2% | 38.9%–100.0% | 1: 72.2%, 3: 83.3% | 28.350 | 20.262 | 4911 / 50167 | unknown |
| deepseek-chat | 61.1% | 27.8%–94.4% | 1: 61.1%, 3: 66.7% | 5.540 | 5.221 | 3045 / 11789 | unknown |
| grok-4.3 | 50.0% | 16.7%–83.3% | 1: 50.0%, 3: 50.0% | 15.348 | 14.886 | 6291 / 7328 | unknown |
| claude-haiku-4-5 | 44.4% | 11.1%–77.8% | 1: 44.4%, 3: 66.7% | 10.394 | 10.692 | 3480 / 16681 | unknown |

## Per-task passes / attempts

| Task | gpt-6-sol | claude-opus-5-5 | claude-sonnet-5 | deepseek-chat | grok-4.3 | claude-haiku-4-5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| arithmetic | 3/3 | 3/3 | 0/3 | 0/3 | 0/3 | 0/3 |
| intervals | 3/3 | 3/3 | 1/3 | 2/3 | 0/3 | 1/3 |
| json_path | 3/3 | 3/3 | 3/3 | 0/3 | 0/3 | 0/3 |
| lru_ttl | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 1/3 |
| rate_limiter | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| roman | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |

## Pass@1 by category

| Category | Tasks | gpt-6-sol | claude-opus-5-5 | claude-sonnet-5 | deepseek-chat | grok-4.3 | claude-haiku-4-5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| uncategorized | 6 | 100.0% | 100.0% | 72.2% | 61.1% | 50.0% | 44.4% |

## Paired comparisons where intervals overlap

- gpt-6-sol − claude-opus-5-5: +0.0% (paired 95% CI +0.0% to +0.0%). Intervals overlap and the paired 95% interval for the difference includes zero: no reliable difference between gpt-6-sol and claude-opus-5-5 on these 6 tasks.
- gpt-6-sol − claude-sonnet-5: +27.8% (paired 95% CI +0.0% to +61.1%). Intervals overlap and the paired 95% interval for the difference includes zero: no reliable difference between gpt-6-sol and claude-sonnet-5 on these 6 tasks.
- claude-opus-5-5 − claude-sonnet-5: +27.8% (paired 95% CI +0.0% to +61.1%). Intervals overlap and the paired 95% interval for the difference includes zero: no reliable difference between claude-opus-5-5 and claude-sonnet-5 on these 6 tasks.
- claude-sonnet-5 − deepseek-chat: +11.1% (paired 95% CI -16.7% to +50.0%). Intervals overlap and the paired 95% interval for the difference includes zero: no reliable difference between claude-sonnet-5 and deepseek-chat on these 6 tasks.
- claude-sonnet-5 − grok-4.3: +22.2% (paired 95% CI +0.0% to +55.6%). Intervals overlap and the paired 95% interval for the difference includes zero: no reliable difference between claude-sonnet-5 and grok-4.3 on these 6 tasks.
- claude-sonnet-5 − claude-haiku-4-5: +27.8% (paired 95% CI +0.0% to +61.1%). Intervals overlap and the paired 95% interval for the difference includes zero: no reliable difference between claude-sonnet-5 and claude-haiku-4-5 on these 6 tasks.
- deepseek-chat − grok-4.3: +11.1% (paired 95% CI +0.0% to +33.3%). Intervals overlap and the paired 95% interval for the difference includes zero: no reliable difference between deepseek-chat and grok-4.3 on these 6 tasks.
- deepseek-chat − claude-haiku-4-5: +16.7% (paired 95% CI +0.0% to +38.9%). Intervals overlap and the paired 95% interval for the difference includes zero: no reliable difference between deepseek-chat and claude-haiku-4-5 on these 6 tasks.
- grok-4.3 − claude-haiku-4-5: +5.6% (paired 95% CI -16.7% to +33.3%). Intervals overlap and the paired 95% interval for the difference includes zero: no reliable difference between grok-4.3 and claude-haiku-4-5 on these 6 tasks.

Reported totals may be partial. Usage coverage (attempts with input/output/cost):

- gpt-6-sol: 18/18/0 of 18.
- claude-opus-5-5: 18/18/0 of 18.
- claude-sonnet-5: 18/18/0 of 18.
- deepseek-chat: 18/18/0 of 18.
- grok-4.3: 18/18/0 of 18.
- claude-haiku-4-5: 18/18/0 of 18.
