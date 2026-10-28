# Context engineering: a testable design decision

Status: offline paired-analysis tooling implemented. No new live context experiment
or model-quality finding is claimed here. Existing October model runs did not test
full versus trimmed context and must not be presented as doing so.

## What the project takes from the resources

[Anthropic's context engineering article](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents)
argues for selecting relevant information rather than filling the context window.
For a coding benchmark this is a hypothesis to test, not a guarantee that shorter
prompts improve correctness. Removing a necessary constraint can make results worse.
Keep the task contract and starter code intact. Never expose hidden tests or reference
solutions as extra context.

The harness already separates generation from deterministic hidden pytest grading,
stores evidence and resumes interrupted runs. None of that requires an orchestration
framework. [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
also supports starting with simple, measurable workflows before adding complexity.

## Offline comparison

```bash
agent-eval compare-context runs/full/results.jsonl runs/trimmed/results.jsonl \
  --seed 20261021 --resamples 2000 --out comparison.json
```

This command reads existing results only. It makes no model calls. Each file must
contain one model label and exactly the same unique task/repeat pairs, with the same
runner for each pair. Labels may distinguish variants. Missing pairs and duplicates
fail rather than silently narrowing the sample.

Output is trimmed minus full: task-macro pass@1 difference with a paired task-level
bootstrap interval, mean paired wall-time difference, and complete reported token
totals. If any token count is missing, that variant's total and its difference stay
null. Mock inputs test the analysis path; they do not measure model capability.

## Before a live experiment

- Pin actual provider/model/version, temperature, token budget, retry policy and
  isolation. Keep the same task IDs, hidden tests and starter sources; verify hashes
  in both run metadata files. The comparison command cannot prove these match.
- Save both context variants and hashes. Declare what is removed before running;
  do not trim using knowledge of test failures. Treat task descriptions as data.
- Counterbalance run order. Record all failures and retries, including timeouts.
  Do not drop inconvenient attempts. Run enough diverse tasks and repeats for the
  intended conclusion; an interval including zero is not evidence of equivalence.
- Existing task specs contain the prompt. If separate task copies carry variants,
  preserve stable IDs and verify hidden-test/starter hashes while recording the
  intentional prompt hash difference. A changed task contract invalidates the comparison.
- Obtain approval for live model costs. No live experiment is enabled by this doc.

## Observability without changing the judge

[Langfuse](https://langfuse.com/docs) can add spans for model calls, retries and latency.
It is not installed or configured here. A future adapter should join on run/attempt ID,
redact secrets and private task content before export, and leave JSONL evidence as the
local record. Trace availability must not decide whether an attempt passed. API costs,
hosting, retention and third-party data disclosure need separate decisions.

[Ragas](https://docs.ragas.io/) is worth considering for a separate retrieval-backed
track. Retrieval faithfulness and coding correctness answer different questions;
LLM-judged scores must not replace hidden tests or be called ground truth.
