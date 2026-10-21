# Contributing

## Setup and checks

```sh
make install                  # Python 3.11+; creates .venv with the dev extras
make lint typecheck test      # ruff check + format check, mypy --strict, pytest
make demo                     # offline end-to-end run
```

CI runs the same checks on Python 3.11 and 3.12. Pull requests should pass all of them.

## Code

- Keep runtime dependencies to the current four (pydantic, PyYAML, httpx, jinja2) unless
  there is a strong reason to add one.
- `mypy --strict` covers `src/` and `tests/`.
- Behaviour changes need tests, including the failure path. Coverage is measured with branches
  and must stay at or above 85% (`pyproject.toml`).
- Tests must not touch the network. Use `httpx.MockTransport` for HTTP runners and the `mock`
  runner or a registered fake for engine tests.
- Never save response bodies, request URLs or headers from HTTP errors. They can contain
  credentials.

## Tasks

A new task needs a precise prompt, a `category`, hidden pytest files with at least 8 tests, and
an independent reference solution saved as `tests/fixtures/reference/<task_id>.py`, outside the
task directory. Bug-fix tasks also need a `starter` file and an issue-style prompt. See
[docs/reference.md](docs/reference.md#writing-a-task). Before submitting:

- `agent-eval validate-task tasks/<id>/task.yaml --reference tests/fixtures/reference/<id>.py`
  passes;
- `pytest tests/test_task_suite.py` passes: no hidden test may pass on an empty module or on a
  stub whose every call returns `None`, and a bug-fix starter must fail at least one hidden test
  and pass at least one;
- the tests cover invalid input and exact boundaries, and include at least one case that a
  plausible but incomplete solution fails;
- every behaviour the tests check is stated in the prompt.

## Code scanning

CodeQL (`security-and-quality` queries) scans the harness, its tests, the hidden tests and the
reference solutions. [`.github/codeql/codeql-config.yml`](.github/codeql/codeql-config.yml)
excludes evaluation data that is not project code:

- `results/**`: what each model wrote during a measured run, committed byte-for-byte as
  evidence. It includes code with bugs, unused imports, a syntax error and a ReDoS-prone regex,
  because that is what the models produced. Editing those files to silence an alert would falsify
  the record, so they are not scanned.
- `tasks/*/starter.py`: the deliberately buggy modules handed to the model in bug-fix tasks.

Hidden test files are hashed into each measured run's `metadata.json`, so changing one breaks
that run's integrity check and `--resume`. Fix an alert in a hidden test only together with a
new measured run, and only if the fix leaves what the tests check unchanged. Four alerts are
currently left on purpose:

- `tasks/undo_buffer/hidden_tests.py`, "unreachable statement": a false positive. The
  assertions after `with pytest.raises(RuntimeError), buf.group(): ... raise` run, because
  `pytest.raises` swallows the exception.
- `tasks/fix_binary_search/hidden_tests.py`, "missing `__eq__`" and "raise in special method":
  `Probe` is a list subclass that counts reads. It is never compared, so list equality is fine,
  and its `__iter__` raises `AssertionError` on purpose so that a solution which iterates
  (instead of staying O(log n)) fails the test.
- `tasks/ledger/hidden_tests.py`, "catch BaseException": the worker thread records any exception,
  and the test then asserts that none occurred.

## Pull requests

Describe the problem, the change, and how you verified it. Don't commit `runs/`, `dist/`,
coverage files or anything containing credentials. Report security issues as described in
[SECURITY.md](SECURITY.md), not in a public issue.
