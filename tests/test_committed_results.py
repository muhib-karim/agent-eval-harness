"""The measured runs committed under results/ are evidence, so they must stay verifiable.

Each run's ``metadata.json`` holds SHA-256 hashes of the task specs, hidden tests and starters
it was graded with. The newest run describes the suite as it is now: editing one of those
files without publishing a new measured run would leave results that no longer match the
tests in the tree. Older runs are history; their task files have since changed on purpose.
"""

import hashlib
import json
from pathlib import Path

import pytest

from agent_eval.results import load_attempts

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
RUNS = sorted(path for path in RESULTS.glob("*-measured") if path.is_dir())

pytestmark = pytest.mark.skipif(not RUNS, reason="results/ is not part of the sdist")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize("run", RUNS, ids=lambda run: run.name)
def test_every_recorded_attempt_has_its_evidence(run: Path) -> None:
    attempts = load_attempts(run / "results.jsonl")
    directories = sorted(f"attempts/{path.name}" for path in (run / "attempts").iterdir())
    assert sorted(attempt.artifacts for attempt in attempts) == directories
    for attempt in attempts:
        for filename in ("model-output.txt", "test.log"):
            assert (run / attempt.artifacts / filename).is_file(), attempt.attempt_id


def test_newest_measured_run_still_matches_the_task_files() -> None:
    run = RUNS[-1]
    metadata = json.loads((run / "metadata.json").read_text(encoding="utf-8"))
    configs = {sha256(path) for path in (ROOT / "examples").glob("*.yaml")}
    assert metadata["config_sha256"] in configs, "the run's config is no longer in examples/"
    # Paths were made relative to the repository root when the evidence was committed.
    hashed = {
        path: digest for files in metadata["task_hashes"].values() for path, digest in files.items()
    }
    assert hashed
    changed = [path for path, digest in hashed.items() if sha256(ROOT / path) != digest]
    assert not changed, (
        f"{run.name} was graded with different versions of {changed}; "
        "publish a new measured run together with the change"
    )
