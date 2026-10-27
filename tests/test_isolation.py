"""Docker isolation, exercised with a fake docker client instead of a real daemon."""

import asyncio
import json
import os
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from agent_eval import isolation
from agent_eval.cli import main
from agent_eval.engine import run_config
from agent_eval.grader import grade
from agent_eval.isolation import (
    IsolationOptions,
    Sandbox,
    container_path,
    docker_command,
    host_user,
    probe_docker,
    select_isolation,
)
from agent_eval.results import load_attempts
from agent_eval.runners.local import CLIRunner
from agent_eval.specs import load_config, load_task

IMAGE = "fake-image"
# Records each invocation, answers `version`, and runs `run`'s inner command on the host
# with /work mapped back to the bind-mounted workdir. The daemon's containers are files in
# a state directory: `run` registers its --name until the inner command exits (like --rm),
# `rm --force` and `kill` unregister, `container inspect` reports existence. Marker files
# there change the daemon: `_race` creates the container only once the first cleanup call
# has looked, `_keep` leaves it behind when the client exits, `_stuck` makes `rm` fail.
FAKE_DOCKER = """#!{python}
import json, os, re, subprocess, sys
args = sys.argv[1:]
with open({log!r}, "a") as stream:
    stream.write(json.dumps(args) + "\\n")
state = {state!r}
def marker(name):
    return os.path.exists(os.path.join(state, name))
def path(name, pending=False):
    return os.path.join(state, ("_pending-" if pending else "") + name)
if args[0] == "version":
    print("27.0.0")
    raise SystemExit(0)
if args[0] in ("rm", "kill", "container"):
    name = args[-1]
    exists = os.path.exists(path(name))
    if os.path.exists(path(name, pending=True)):
        os.replace(path(name, pending=True), path(name))
    if args[0] == "container":
        print(json.dumps([{{"Name": name}}]) if exists else f"Error: No such container: {{name}}")
        raise SystemExit(0 if exists else 1)
    if not exists:
        print(f"Error response from daemon: No such container: {{name}}")
        raise SystemExit(1)
    if marker("_stuck"):
        print("Error response from daemon: removal of container in progress")
        raise SystemExit(1)
    os.remove(path(name))
    raise SystemExit(0)
assert args[0] == "run", args
valued = {{"--name", "--label", "--network", "--memory", "--memory-swap", "--cpus",
          "--pids-limit", "--tmpfs", "--cap-drop", "--security-opt", "--user", "--mount",
          "--workdir", "--env", "--entrypoint"}}
index, mount, name = 1, None, None
while args[index].startswith("--"):
    if args[index] == "--mount":
        mount = dict(part.split("=", 1) for part in args[index + 1].split(","))
    if args[index] == "--name":
        name = args[index + 1]
    index += 2 if args[index] in valued else 1
assert args[index] == {image!r}, args
open(path(name, pending=marker("_race")), "w").close()
host = mount["source"]
inner = [re.sub(r"(?<![\\w/])/work(?=/|$)", lambda _: host, part) for part in args[index + 1:]]
if inner[0] == "python":
    inner[0] = sys.executable
code = subprocess.run(inner, cwd=host).returncode
if not marker("_keep") and os.path.exists(path(name)):
    os.remove(path(name))
raise SystemExit(code)
"""


def calls(log: Path) -> list[list[str]]:
    return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []


def containers(log: Path) -> list[str]:
    """Containers the fake daemon still has, created or about to be."""
    return sorted(
        p.name.removeprefix("_pending-")
        for p in (log.parent / "containers").iterdir()
        if p.name.startswith(("agent-eval-", "_pending-"))
    )


def daemon_marker(log: Path, name: str) -> None:
    (log.parent / "containers" / name).touch()


@pytest.fixture
def fake_docker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    log = tmp_path / "docker-calls.jsonl"
    state = tmp_path / "containers"
    state.mkdir()
    path = tmp_path / "bin" / "docker"
    path.parent.mkdir()
    path.write_text(
        FAKE_DOCKER.format(python=sys.executable, log=str(log), state=str(state), image=IMAGE)
    )
    path.chmod(0o755)
    monkeypatch.setattr(isolation, "CLEANUP_DELAY_S", 0.05)
    return path, log


def options(docker: Path, **extra: Any) -> IsolationOptions:
    return IsolationOptions(mode="docker", image=IMAGE, docker=str(docker), **extra)


def value_of(argv: list[str], flag: str) -> list[str]:
    return [argv[i + 1] for i, part in enumerate(argv) if part == flag]


def test_defaults() -> None:
    assert IsolationOptions().model_dump() == {
        "mode": "local",
        "image": "python:3.12-slim",
        "network": "none",
        "memory": "2g",
        "cpus": 2.0,
        "pids_limit": 256,
        "docker": "docker",
    }


def test_docker_command_flags(tmp_path: Path) -> None:
    workdir = tmp_path / "work"
    workdir.mkdir()
    command = ["agent", "--prompt-file", str(workdir / "p.txt"), f"--out={workdir}", "-q"]
    argv = docker_command(
        IsolationOptions(memory="512m", cpus=1.5, pids_limit=64),
        command,
        workdir,
        name="agent-eval-x",
        env_names=["API_KEY", "LANG"],
        user="1000:1000",
    )
    assert argv[:3] == ["docker", "run", "--rm"]
    assert value_of(argv, "--name") == ["agent-eval-x"]
    assert value_of(argv, "--network") == ["none"]
    assert value_of(argv, "--memory") == value_of(argv, "--memory-swap") == ["512m"]
    assert value_of(argv, "--cpus") == ["1.5"]
    assert value_of(argv, "--pids-limit") == ["64"]
    assert "--read-only" in argv
    assert value_of(argv, "--tmpfs") == ["/tmp:rw,nosuid,nodev,size=256m"]
    assert value_of(argv, "--cap-drop") == ["ALL"]
    assert value_of(argv, "--security-opt") == ["no-new-privileges"]
    assert value_of(argv, "--user") == ["1000:1000"]
    assert value_of(argv, "--mount") == [f"type=bind,source={workdir.resolve()},target=/work"]
    assert value_of(argv, "--workdir") == ["/work"]
    assert value_of(argv, "--entrypoint") == [""]
    assert value_of(argv, "--env") == ["API_KEY", "LANG"]
    image = argv.index("python:3.12-slim")
    assert argv[image + 1 :] == ["agent", "--prompt-file", "/work/p.txt", "--out=/work", "-q"]
    assert all(str(workdir) not in part for part in argv if not part.startswith("type=bind"))


def test_docker_command_network_opt_in_and_no_user(tmp_path: Path) -> None:
    argv = docker_command(
        IsolationOptions(network="bridge", docker="/opt/docker"),
        ["true"],
        tmp_path,
        name="n",
        env_names=[],
    )
    assert argv[0] == "/opt/docker"
    assert value_of(argv, "--network") == ["bridge"]
    assert "--user" not in argv and "--env" not in argv


def test_docker_command_rejects_unmountable_paths(tmp_path: Path) -> None:
    workdir = tmp_path / "a,b"
    workdir.mkdir()
    with pytest.raises(ValueError, match="cannot be bind-mounted"):
        docker_command(IsolationOptions(), ["true"], workdir, name="n", env_names=[])


def test_container_path_rewrites_whole_components(tmp_path: Path) -> None:
    workdir = tmp_path / "w"
    assert container_path(str(workdir), workdir) == "/work"
    assert container_path(f"{workdir}/a/b.py", workdir) == "/work/a/b.py"
    assert container_path(f"--junitxml={workdir}/r.xml", workdir) == "--junitxml=/work/r.xml"
    assert container_path(f"{workdir}2/x", workdir) == f"{workdir}2/x"
    assert container_path("unrelated", workdir) == "unrelated"


def test_container_path_converts_windows_separators() -> None:
    workdir = PureWindowsPath(r"C:\x\attempt")
    assert container_path(r"C:\x\attempt\_agent_prompt.txt", workdir) == "/work/_agent_prompt.txt"
    assert container_path(r"--out=C:\x\attempt\a\b.py", workdir) == "--out=/work/a/b.py"
    assert container_path(r"C:\x\attempt", workdir) == "/work"
    assert container_path(r"C:\x\attempt2\y", workdir) == r"C:\x\attempt2\y"
    # On POSIX hosts a backslash is part of a file name and stays.
    assert container_path("/tmp/w/a\\b", PurePosixPath("/tmp/w")) == "/work/a\\b"


def test_host_user(monkeypatch: pytest.MonkeyPatch) -> None:
    if os.name == "posix":
        assert host_user() == f"{os.getuid()}:{os.getgid()}"
    monkeypatch.setattr(os, "name", "nt")
    assert host_user() is None


@pytest.mark.parametrize(
    "fields",
    [
        {"mode": "podman"},
        {"network": "host"},
        {"memory": "lots"},
        {"memory": "-1g"},
        {"cpus": 0},
        {"cpus": float("inf")},
        {"pids_limit": 0},
        {"pids_limit": "64"},
        {"image": "--privileged"},
        {"image": ""},
        {"docker": ""},
        {"privileged": True},
    ],
)
def test_invalid_options(fields: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        IsolationOptions.model_validate(fields)


def test_client_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DOCKER_CONFIG", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("DOCKER_HOST", "unix:///run/docker.sock")
    monkeypatch.setenv("SECRET_TOKEN", "x" * 20)
    env = isolation.client_environment()
    assert env["DOCKER_CONFIG"] == str(tmp_path / ".docker")
    assert env["DOCKER_HOST"] == "unix:///run/docker.sock"
    assert "SECRET_TOKEN" not in env and "HOME" not in env
    monkeypatch.setenv("DOCKER_CONFIG", "/etc/docker-client")
    assert isolation.client_environment()["DOCKER_CONFIG"] == "/etc/docker-client"


def test_client_environment_without_a_home(monkeypatch: pytest.MonkeyPatch) -> None:
    def no_home() -> Path:
        raise RuntimeError("no home")

    monkeypatch.delenv("DOCKER_CONFIG", raising=False)
    monkeypatch.setattr(Path, "home", no_home)
    assert "DOCKER_CONFIG" not in isolation.client_environment()


def test_config_block_and_cli_flag_precedence(
    config_path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert load_config(config_path).isolation.mode == "local"
    data = yaml.safe_load(config_path.read_text())
    data["isolation"] = {"mode": "docker", "network": "bridge", "memory": "1g"}
    config_path.write_text(yaml.safe_dump(data))
    config = load_config(config_path)
    assert config.isolation.network == "bridge" and config.isolation.memory == "1g"

    async def no_probe(options: IsolationOptions) -> str | None:
        raise AssertionError("local mode must not probe docker")

    monkeypatch.setattr(isolation, "probe_docker", no_probe)
    out = tmp_path / "local"
    assert main(["run", str(config_path), "--out", str(out), "--isolation", "local"]) == 0
    rows = load_attempts(out / "results.jsonl")
    assert {(r.isolation.requested, r.isolation.used) for r in rows if r.isolation} == {
        ("local", "local")
    }
    assert all(r.isolation is not None and r.isolation.warning is None for r in rows)
    resolved = yaml.safe_load((out / "config.resolved.yaml").read_text())
    assert resolved["isolation"]["network"] == "bridge"


def test_fallback_records_the_warning(
    config_path: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = yaml.safe_load(config_path.read_text())
    data["isolation"] = {"docker": str(tmp_path / "missing" / "docker")}
    config_path.write_text(yaml.safe_dump(data))
    out = tmp_path / "run"
    assert main(["run", str(config_path), "--out", str(out), "--isolation", "docker"]) == 0
    err = capsys.readouterr().err
    assert err.count("warning: docker isolation unavailable") == 1
    assert "docker executable not found" in err
    lines = [json.loads(line) for line in (out / "results.jsonl").read_text().splitlines()]
    assert len(lines) == 4
    for line in lines:
        assert line["isolation"]["requested"] == "docker"
        assert line["isolation"]["used"] == "local"
        assert "attempts ran with the local runner" in line["isolation"]["warning"]
    # The fallback still grades: the mock reference passes locally.
    assert {line["outcome"] for line in lines} == {"pass", "fail"}


def test_probe_failures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    failing = tmp_path / "failing-docker"
    failing.write_text(f"#!{sys.executable}\nraise SystemExit(1)\n")
    failing.chmod(0o755)
    silent = tmp_path / "silent-docker"
    silent.write_text(f"#!{sys.executable}\n")
    silent.chmod(0o755)
    slow = tmp_path / "slow-docker"
    slow.write_text(f"#!{sys.executable}\nimport time\ntime.sleep(30)\n")
    slow.chmod(0o755)
    assert asyncio.run(probe_docker(options(failing))) == "docker daemon is unreachable"
    assert asyncio.run(probe_docker(options(silent))) == "docker daemon is unreachable"
    monkeypatch.setattr(isolation, "PROBE_TIMEOUT_S", 0.3)
    assert asyncio.run(probe_docker(options(slow))) == "docker daemon did not answer within 0.3 s"
    sandbox, record = asyncio.run(select_isolation(options(failing)))
    assert sandbox is None and record.used == "local"


def test_grading_in_docker(fake_docker: tuple[Path, Path], task_path: Path, workdir: Path) -> None:
    docker, log = fake_docker
    sandbox, record = asyncio.run(select_isolation(options(docker)))
    assert sandbox is not None and record.model_dump() == {
        "requested": "docker",
        "used": "docker",
        "warning": None,
    }
    task = load_task(task_path)
    (workdir / "solution.py").write_text("def answer():\n    return 42\n")
    result = asyncio.run(grade(task, task_path, workdir, sandbox))
    assert (result.outcome, result.passed, result.total) == ("pass", 1, 1)
    version, run = calls(log)
    assert version == ["version", "--format", "{{.Server.Version}}"]
    inner = run[run.index(IMAGE) + 1 :]
    assert inner[:2] == ["python", "-I"]
    assert value_of(inner, "-c")[1] == "/dev/null"
    assert "--rootdir" in inner and inner[inner.index("--rootdir") + 1] == "/work"
    assert any(part.startswith("--junitxml=/work/_hidden_") for part in inner)
    assert str(workdir) not in json.dumps(inner)
    assert set(value_of(run, "--env")) >= {"PYTEST_DISABLE_PLUGIN_AUTOLOAD", "HOME", "TMPDIR"}
    assert "PATH" not in value_of(run, "--env")


def test_cli_agent_in_docker_passes_env_by_name(
    fake_docker: tuple[Path, Path],
    task_path: Path,
    workdir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docker, log = fake_docker
    monkeypatch.setenv("AGENT_SECRET", "s3cret-value-123")
    code = (
        "import os, sys; prompt = open(sys.argv[1]).read(); "
        "print(os.environ['AGENT_SECRET'][::-1]); "
        "assert os.environ['HOME'] == '/tmp'; "
        "open(os.path.join(sys.argv[2], 'solution.py'), 'w').write("
        "'def answer():\\n    return 42\\n'); print('agent done')"
    )
    runner = CLIRunner(
        {
            "command": [sys.executable, "-c", code, "{prompt_file}", "{workdir}"],
            "env_passthrough": ["AGENT_SECRET"],
            "isolate_home": True,
        }
    )
    runner.sandbox = Sandbox(options(docker))
    generation = asyncio.run(runner.generate(load_task(task_path), workdir))
    assert "agent done" in generation.raw_output
    assert "321-eulav-terc3s" in generation.raw_output
    assert (workdir / "solution.py").is_file()
    (run,) = calls(log)
    assert "AGENT_SECRET" in value_of(run, "--env")
    assert "s3cret-value-123" not in json.dumps(run)
    assert run[-2:] == ["/work/_agent_prompt.txt", "/work"]


SLEEP = [sys.executable, "-c", "import time; time.sleep(30)"]


def test_clean_exit_needs_no_cleanup(fake_docker: tuple[Path, Path], workdir: Path) -> None:
    docker, log = fake_docker
    result = asyncio.run(Sandbox(options(docker)).run([sys.executable, "-c", ""], workdir, 30, {}))
    assert result.returncode == 0
    assert [c[0] for c in calls(log)] == ["run"]
    assert containers(log) == []


def test_containers_carry_a_label(tmp_path: Path) -> None:
    argv = docker_command(IsolationOptions(), ["true"], tmp_path, name="n", env_names=[])
    assert value_of(argv, "--label") == ["agent-eval.attempt=n"]


def test_timeout_removes_the_container(fake_docker: tuple[Path, Path], workdir: Path) -> None:
    docker, log = fake_docker
    result = asyncio.run(Sandbox(options(docker)).run(SLEEP, workdir, 0.5, {}))
    assert result.timed_out
    assert "could not be removed" not in result.output
    run, rm, *rest = calls(log)
    (name,) = value_of(run, "--name")
    assert rm == ["rm", "--force", name]
    assert ["container", "inspect", name] in rest
    assert containers(log) == []


def test_cancellation_removes_the_container(fake_docker: tuple[Path, Path], workdir: Path) -> None:
    docker, log = fake_docker
    sandbox = Sandbox(options(docker))

    async def cancel_soon() -> None:
        task = asyncio.create_task(sandbox.run(SLEEP, workdir, 30, {}))
        while not containers(log):
            await asyncio.sleep(0.05)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(cancel_soon())
    run, rm, *_ = calls(log)
    assert rm == ["rm", "--force", *value_of(run, "--name")]
    assert containers(log) == []


def test_non_zero_exit_removes_a_leftover_container(
    fake_docker: tuple[Path, Path], workdir: Path
) -> None:
    docker, log = fake_docker
    # The client fails while the daemon keeps the container.
    daemon_marker(log, "_keep")
    command = [sys.executable, "-c", "print('boom'); raise SystemExit(3)"]
    result = asyncio.run(Sandbox(options(docker)).run(command, workdir, 30, {}))
    assert (result.returncode, result.timed_out) == (3, False)
    assert "boom" in result.output and "could not be removed" not in result.output
    run, rm, inspect = calls(log)
    (name,) = value_of(run, "--name")
    assert (rm, inspect) == (["rm", "--force", name], ["container", "inspect", name])
    assert containers(log) == []


def test_container_created_after_the_first_check_is_removed(
    fake_docker: tuple[Path, Path], workdir: Path
) -> None:
    docker, log = fake_docker
    # The daemon starts the container only after cleanup has first found nothing.
    daemon_marker(log, "_race")
    result = asyncio.run(Sandbox(options(docker)).run(SLEEP, workdir, 0.5, {}))
    assert result.timed_out and "could not be removed" not in result.output
    run, *cleanup = calls(log)
    (name,) = value_of(run, "--name")
    assert cleanup[:2] == [["rm", "--force", name], ["container", "inspect", name]]
    assert cleanup.count(["rm", "--force", name]) >= 2
    assert containers(log) == []


def test_cleanup_failure_is_reported_without_masking_the_result(
    fake_docker: tuple[Path, Path], workdir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    docker, log = fake_docker
    daemon_marker(log, "_stuck")
    sandbox = Sandbox(options(docker))
    result = asyncio.run(sandbox.run(SLEEP, workdir, 0.5, {}))
    (name,) = containers(log)
    assert result.timed_out
    assert result.output.endswith(f"[agent-eval: container {name} could not be removed]\n")
    assert f"container {name} could not be removed" in capsys.readouterr().err
    rms = [c for c in calls(log) if c[0] == "rm"]
    assert len(rms) == isolation.CLEANUP_ROUNDS

    daemon_marker(log, "_keep")
    command = [sys.executable, "-c", "raise SystemExit(4)"]
    result = asyncio.run(sandbox.run(command, workdir, 30, {}))
    assert (result.returncode, result.timed_out) == (4, False)
    assert "could not be removed" in result.output


def test_cleanup_is_bounded_in_time(
    fake_docker: tuple[Path, Path], workdir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    docker, log = fake_docker
    daemon_marker(log, "_stuck")
    monkeypatch.setattr(isolation, "CLEANUP_DELAY_S", 10.0)
    monkeypatch.setattr(isolation, "CLEANUP_BUDGET_S", 0.5)
    sandbox = Sandbox(options(docker))

    async def timed() -> float:
        loop = asyncio.get_running_loop()
        start = loop.time()
        assert not await sandbox.remove("agent-eval-x", workdir, settle=True)
        return loop.time() - start

    assert asyncio.run(timed()) < 5.0
    assert calls(log)[:2] == [
        ["rm", "--force", "agent-eval-x"],
        ["container", "inspect", "agent-eval-x"],
    ]


def test_cleanup_tolerates_a_missing_client(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(isolation, "CLEANUP_DELAY_S", 0.01)
    sandbox = Sandbox(options(tmp_path / "missing"))
    with pytest.raises(OSError):
        asyncio.run(sandbox.run(["true"], tmp_path, 5, {}))
    assert "could not be removed" in capsys.readouterr().err


def test_engine_runs_attempts_in_containers(
    fake_docker: tuple[Path, Path], config_path: Path, tmp_path: Path
) -> None:
    docker, log = fake_docker
    data = yaml.safe_load(config_path.read_text())
    code = (
        "import sys; open(sys.argv[1] + '/solution.py', 'w')"
        ".write('def answer():\\n    return 42\\n')"
    )
    data["models"].append(
        {
            "name": "agent",
            "runner": "cli",
            "options": {"command": [sys.executable, "-c", code, "{workdir}"]},
        }
    )
    data["isolation"] = {"mode": "docker", "image": IMAGE, "docker": str(docker)}
    config_path.write_text(yaml.safe_dump(data))
    attempts = asyncio.run(run_config(config_path, tmp_path / "run"))
    assert {(a.model, a.outcome) for a in attempts} == {
        ("correct", "pass"),
        ("wrong", "fail"),
        ("agent", "pass"),
    }
    assert all(a.isolation is not None and a.isolation.used == "docker" for a in attempts)
    invocations = calls(log)
    assert [c[0] for c in invocations].count("version") == 1
    runs = [c for c in invocations if c[0] == "run"]
    # Six gradings plus two agent generations, each in its own container.
    assert len(runs) == 8
    assert len({value_of(c, "--name")[0] for c in runs}) == 8


def test_old_results_without_isolation_still_load_and_resume(
    config_path: Path, tmp_path: Path
) -> None:
    out = tmp_path / "run"
    asyncio.run(run_config(config_path, out))
    lines = (out / "results.jsonl").read_text().splitlines()
    old = []
    for line in lines[:2]:
        row = json.loads(line)
        del row["isolation"], row["category"]
        old.append(json.dumps(row))
    (out / "results.jsonl").write_text("\n".join(old) + "\n")
    assert "isolation" not in (out / "config.resolved.yaml").read_text()
    resumed = asyncio.run(run_config(config_path, out, resume=True))
    assert len(resumed) == 4
    rows = load_attempts(out / "results.jsonl")
    assert sum(row.isolation is None for row in rows) == 2
    assert main(["report", str(out / "results.jsonl")]) == 0


def docker_config(config_path: Path, docker: Path) -> None:
    """Docker settings in the config, but the local mode unless --isolation says otherwise."""
    data = yaml.safe_load(config_path.read_text())
    data["isolation"] = {"image": IMAGE, "docker": str(docker)}
    config_path.write_text(yaml.safe_dump(data))


def interrupt(out: Path) -> None:
    """Keep only the first recorded attempt, as if the run had been interrupted."""
    lines = (out / "results.jsonl").read_text().splitlines()
    (out / "results.jsonl").write_text(lines[0] + "\n")


def test_resume_refuses_a_different_isolation_mode(
    fake_docker: tuple[Path, Path], config_path: Path, tmp_path: Path
) -> None:
    docker, _ = fake_docker
    docker_config(config_path, docker)
    out = tmp_path / "run"
    asyncio.run(run_config(config_path, out, isolation="docker"))
    assert yaml.safe_load((out / "config.resolved.yaml").read_text())["isolation"]["mode"] == (
        "docker"
    )
    interrupt(out)
    with pytest.raises(ValueError, match=r"config differs .*\(isolation docker, now local\)"):
        asyncio.run(run_config(config_path, out, resume=True))
    with pytest.raises(ValueError, match="config differs"):
        asyncio.run(run_config(config_path, out, resume=True, isolation="local"))
    resumed = asyncio.run(run_config(config_path, out, resume=True, isolation="docker"))
    assert len(resumed) == 4
    rows = load_attempts(out / "results.jsonl")
    assert all(row.isolation is not None and row.isolation.used == "docker" for row in rows)


def test_cli_isolation_flag_is_recorded_without_a_config_block(
    config_path: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "run"
    # Docker is unavailable, so attempts fall back, but docker was what the run asked for.
    assert main(["run", str(config_path), "--out", str(out), "--isolation", "docker"]) == 0
    assert (
        yaml.safe_load((out / "config.resolved.yaml").read_text())["isolation"]["mode"]
        == ("docker")
        or "isolation unavailable" in capsys.readouterr().err
    )
    interrupt(out)
    assert main(["run", str(config_path), "--out", str(out), "--resume"]) == 2
    assert "isolation docker, now local" in capsys.readouterr().err


def test_legacy_run_without_isolation_entry_resumes_as_local(
    fake_docker: tuple[Path, Path], config_path: Path, tmp_path: Path
) -> None:
    docker, _ = fake_docker
    out = tmp_path / "run"
    asyncio.run(run_config(config_path, out))
    resolved = (out / "config.resolved.yaml").read_text()
    assert "isolation" not in resolved
    interrupt(out)
    assert len(asyncio.run(run_config(config_path, out, resume=True))) == 4
    interrupt(out)
    assert len(asyncio.run(run_config(config_path, out, resume=True, isolation="local"))) == 4
    interrupt(out)
    # Absent means local, so resuming it in docker is a different config.
    docker_config(config_path, docker)
    with pytest.raises(ValueError, match=r"isolation local, now docker"):
        asyncio.run(run_config(config_path, out, resume=True, isolation="docker"))
