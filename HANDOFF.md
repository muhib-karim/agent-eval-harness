# Handoff: agent-eval-harness v1.3.0

Branch `upgrade/v1.3.0`: 26 commits on top of `main` (d44e4e1), all authored and committed as
Muhib Karim. Work was done in five slices by Claude Code with model **claude-opus-5-5**. Item
status: [TASKS.md](TASKS.md). Release text: [RELEASE_NOTES_v1.3.0.md](RELEASE_NOTES_v1.3.0.md).

**State:** acceptance items 1–9 are done. Item 10 is handed to the coordinator: push the two
slice 5 commits (local head, after 4e48f9b), open the PR, merge after CI is green, then tag
`v1.3.0`. The last pushed head, 4e48f9b, is green on CI and CodeQL.

## What changed in 1.3.0

| Area | Change | Main files |
| --- | --- | --- |
| Tasks | 6 → 16 tasks, four per category (`algorithms`, `parsing`, `stateful`, `bug-fix`), 279 hidden tests; `category` and `starter` fields; references moved out of task dirs | `tasks/`, `tests/fixtures/reference/`, `src/agent_eval/specs.py`, `engine.py` |
| Task QA | CI test: each reference passes; no hidden test passes on an empty module or a `None` stub; each bug-fix starter fails ≥ 1 and passes ≥ 1 test | `tests/test_task_suite.py` |
| Statistics | Seeded task-level bootstrap 95% CIs (seed 20261021, 2000 resamples), per-category pass@1, paired bootstrap for overlapping intervals; `report --seed/--resamples` | `src/agent_eval/stats.py`, `results.py` |
| Report | Self-contained HTML (no external assets): keyboard-sortable leaderboard with `aria-sort`, SVG interval rows, paired table, heatmap with numbers, explicit `unknown`, dark mode, 375 px layout | `src/agent_eval/templates/report.html`, `tests/test_report_html.py` |
| Agent CLIs | `claude-code`, `codex`, `opencode` presets; env allow-list for all CLI agents; `isolate_home`; `{prompt}`; Claude Code usage parsing; redaction of forwarded values | `src/agent_eval/runners/presets.py`, `local.py`, `tests/test_cli_presets.py` |
| Runs | `run --resume` (unchanged config and task hashes required; recorded attempts kept) | `engine.py`, `tests/test_resume.py` |
| CI | Named ruff/format/strict-mypy steps, 85% coverage gate + summary, 3.11/3.12 matrix, gitleaks job, CodeQL, Dependabot; release body from `RELEASE_NOTES_<tag>.md` | `.github/` |
| Results | Measured run v2: 6 models × 16 tasks × 3 repeats = 288 attempts, 2026-10-21 17:53:41Z–18:11:34Z | `results/2026-10-21-measured/` incl. `METHODOLOGY.md` |
| Docs | README rewrite with Showcase screenshot; reference docs; CONTRIBUTING; sample report; CHANGELOG `[1.3.0] - 2026-10-21`; version 1.3.0 in pyproject, `__init__`, CITATION.cff; release notes; SKILLS_USED.md | `README.md`, `docs/`, `CHANGELOG.md`, `RELEASE_NOTES_v1.3.0.md` |
| Pages | Landing page = 21 Oct run (+ METHODOLOGY.md); 17 Oct run under `/history/2026-10-17/`; demo at `/demo/` | `.github/workflows/pages.yml` |

Measured run v2, pass@1 (95% CI): claude-sonnet-5-5, claude-opus-5-5, claude-fable-5-1 100%
(100–100); gpt-6-sol 97.9% (93.8–100); claude-sonnet-5 79.2% (60.4–93.8); claude-haiku-4-5
66.7% (47.9–85.4). 27 non-passing attempts (16 fail, 8 error, 3 timeout), none retried, all
explained in `METHODOLOGY.md`. claude-haiku-5-5 also answered the probe but was left out to keep
the run under the attempt budget (288 rather than 336).

## Checks

### RUN — final, slice 5 (local head before this handoff commit, Python 3.11 venv)

```text
$ ruff check .                    -> All checks passed!
$ ruff format --check .           -> 76 files already formatted
$ mypy --strict                   -> Success: no issues found in 29 source files
$ pytest -x -q -p no:cacheprovider
  TOTAL 1037 stmts, 10 miss, 284 branches, 4 partial -> 99%
  Required test coverage of 85.0% reached. Total coverage: 98.94%
  229 passed in 101.91s
$ gitleaks git --log-opts=d44e4e1..HEAD .   -> no leaks found
$ gitleaks dir .                            -> no leaks found
```

- Added lines on the branch (`git diff d44e4e1..HEAD`) grepped for the forbidden names, machine
  paths and token prefixes: no hits. Endpoint hosts and credential values from the environment:
  not in the diff or the tree. All 26 commits on the branch carry the configured
  identity as author and committer.
- Pages assemble step reproduced locally from the committed results: the landing page shows 288
  attempts and the history page 108. The committed `results/2026-10-21-measured/report.html` is
  byte-identical to what the workflow will render.

### RUN — on GitHub Actions (branch `upgrade/v1.3.0`)

| Head | CI run | CodeQL run | Conclusion |
| --- | --- | --- | --- |
| 4e48f9b (slice 4) | 39651870067 | 39651870150 | success / success; CI jobs `checks (3.11)`, `checks (3.12)`, `gitleaks`, `offline-demo`, `docker` all success |
| 187a051 (slice 3) | 39635710585 | 39635710548 | success / success |
| e346a95 (slice 2) | 39633772358 | 39633772492 | success / success |
| 611997a (slice 1) | 39579363695 | 39579363919 | success / success |

The two slice 5 commits (release notes, release-workflow notes file) have not run on CI yet; they
change only a Markdown file and the tag-triggered release workflow.

### RUN — earlier slices (summarised; details in git history of this file)

- Slice 2: every bug-fix starter graded against its hidden tests (fix_binary_search 5/12,
  fix_running_stats 9/13, fix_memoize 6/10, fix_slugify 11/13, all `fail`); the offline demo,
  64 attempts, mock-reference 100% in every category, mock-wrong 0%.
- Slice 3: headless Chromium renders of the report at 1280 px and 375 px, light and dark. These
  fixed misaligned gridlines, leaderboard overflow and clipped mobile captions. A scripted
  click test confirmed the sort buttons, `aria-sort` moves and the live-region text.
- Slice 4: the live run (288/288 recorded, exit 0); 36 task-file hashes and the config hash in
  `metadata.json` match the repository; the scrubbed results were scanned for machine paths,
  hosts and credentials (none); a non-editable `pip install '.[grade]'` in a fresh venv gives
  `agent-eval --version` 1.3.0 and 16 tasks; every README finding was checked against
  `results.jsonl`, and one overstatement was corrected.

### INFERRED — not run

- `pipx install '.[grade]'` (pipx is not installed here; the plain pip path was run).
- Mermaid rendering on GitHub (basic flowchart syntax only; not rendered locally).
- The Pages deployment itself (the workflow runs only on `main`; its commands were run locally).
- The release workflow change and the README/release-notes install line: they work only once
  `v1.3.0` is tagged and the workflow attaches the wheel.
- Screen-reader output of the report (structure checked by tests and markup review, not with
  NVDA/VoiceOver); contrast ratios computed from the colour tokens, not measured with axe.
- The agent-CLI presets against the real claude / codex / opencode binaries (tested with a fake
  CLI only).

## Remaining issues and follow-ups

- **Extraction rule.** Replies with several Python blocks are joined (documented). For
  single-block prompts this turned four claude-haiku-4-5 replies into import errors in the
  measured run. A stricter rule, such as taking the largest block when the prompt asks for one,
  is on the roadmap and was not applied to the recorded results.
- **Stop reason not recorded.** "Used the whole output budget" is inferred from reported output
  tokens equal to `max_tokens`. Recording `stop_reason` would be a small additive schema change.
- **Bug-fix artifact.** When an HTTP runner errors on a bug-fix task, the saved `solution.py` is
  the untouched starter (the outcome is still correctly `error`).
- **Static coverage badge** (98.9%) in the README; CI enforces the 85% gate but doesn't update
  the badge.
- **Suite ceiling.** Four models score 100% or close to it, so the suite cannot rank them; harder
  tasks are the next step.
- Process notes: slice 1 hit its time box before writing a handoff, so slice 2 wrote the first
  one. The slice 4 summary said 13 commits; the correct count is 9.

## For the coordinator

1. Push `upgrade/v1.3.0` (two new commits after 4e48f9b, plus this handoff commit) and confirm
   CI, CodeQL and gitleaks are green on the new head.
2. Open the PR to `main` and merge after review.
3. Tag `v1.3.0` on the merge commit. The release workflow builds and tests the wheel and sdist,
   writes `SHA256SUMS.txt`, and publishes `RELEASE_NOTES_v1.3.0.md` as the release body. The
   README install line works from then on.
4. The Pages workflow on `main` publishes the 21 Oct report as the landing page.
