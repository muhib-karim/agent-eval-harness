"""Docker isolation, exercised with a fake docker client instead of a real daemon."""

import asyncio
import contextlib
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from agent_eval import isolation, process
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
from agent_eval.process import ProcessResult
from agent_eval.results import load_attempts
from agent_eval.runners.local import CLIRunner
from agent_eval.specs import load_config, load_task

IMAGE = "fake-image"
RUN_ID = "run-under-test"
# Records each invocation and keeps the daemon's containers as JSON files in a state
# directory. `create` registers --name with its labels, --env values, mount and command;
# `start --attach` runs the command on the host with /work mapped back to the bind-mounted
# workdir; `rm --force` unregisters; `ps -aq --filter label=K=V` lists the matching names
# registered at that moment, without waiting for creates in flight (docker does not promise
# to). Marker files change the daemon: `_slow_create` makes `create` hang while a detached
# process registers the container once the client has been killed (and `_hold_create` is
# gone), `_create_fails` fails it, `_stuck` makes `rm` fail, `_slow_rm`
# makes `rm` take 0.5 s (writing `_rm_started` first and `_rm_saw_workdir` with whether the
# mount still existed), `_ps_fails` fails `ps`.
# The daemon side of a slow create: announce it, wait until the client is gone and the test
# releases the hold, register. Its pid file exists while it runs, for the leak check.
REGISTER = (
    "import os, sys, time\n"
    "client, pending, final, spec, hold, pids = sys.argv[1:]\n"
    "pid_file = os.path.join(pids, str(os.getpid()))\n"
    "open(pid_file, 'w').close()\n"
    "open(pending, 'w').write(spec)\n"
    "while os.getppid() == int(client) or os.path.exists(hold):\n"
    "    time.sleep(0.01)\n"
    "os.replace(pending, final)\n"
    "os.remove(pid_file)\n"
)
FAKE_DOCKER = """#!{python}
import json, os, re, subprocess, sys, time
args = sys.argv[1:]
with open({log!r}, "a") as stream:
    stream.write(json.dumps(args) + "\\n")
state = {state!r}
def marker(name):
    return os.path.exists(os.path.join(state, name))
def path(name, pending=False):
    return os.path.join(state, ("_pending-" if pending else "") + name)
def load(name):
    if not os.path.exists(path(name)):
        print(f"Error response from daemon: No such container: {{name}}")
        raise SystemExit(1)
    with open(path(name)) as stream:
        return json.load(stream)
command = args[0]
if command == "version":
    print("27.0.0")
    raise SystemExit(0)
if command == "ps":
    if marker("_ps_fails"):
        print("Cannot connect to the Docker daemon")
        raise SystemExit(1)
    assert args[1:3] == ["-aq", "--filter"], args
    label = args[3].removeprefix("label=")
    for name in sorted(os.listdir(state)):
        if not name.startswith("_") and label in load(name)["labels"]:
            print(name)
    raise SystemExit(0)
if command == "rm":
    assert args[1] == "--force", args
    name = args[2]
    spec = load(name)
    if marker("_slow_rm"):
        open(path("_rm_started"), "w").close()
        time.sleep(0.5)
        with open(path("_rm_saw_workdir"), "w") as stream:
            stream.write(str(os.path.isdir(spec["mount"]["source"])))
    if marker("_stuck"):
        print("Error response from daemon: removal of container in progress")
        raise SystemExit(1)
    os.remove(path(name))
    print(name)
    raise SystemExit(0)
if command == "start":
    assert args[1] == "--attach", args
    spec = load(args[2])
    host = spec["mount"]["source"]
    inner = [re.sub(r"(?<![\\w/])/work(?=/|$)", lambda _: host, part) for part in spec["command"]]
    if inner[0] == "python":
        inner[0] = sys.executable
    env = dict(spec["env"], PATH=os.environ["PATH"])
    raise SystemExit(subprocess.run(inner, cwd=host, env=env).returncode)
assert command == "create", args
if marker("_create_fails"):
    print("Unable to find image")
    raise SystemExit(125)
valued = {{"--name", "--label", "--network", "--memory", "--memory-swap", "--cpus",
          "--pids-limit", "--tmpfs", "--cap-drop", "--security-opt", "--user", "--mount",
          "--workdir", "--env", "--entrypoint"}}
index, mount, name, labels, env = 1, None, None, [], {{}}
while args[index].startswith("--"):
    if args[index] == "--env":
        env[args[index + 1]] = os.environ[args[index + 1]]
    if args[index] == "--mount":
        mount = dict(part.split("=", 1) for part in args[index + 1].split(","))
    if args[index] == "--name":
        name = args[index + 1]
    if args[index] == "--label":
        labels.append(args[index + 1])
    index += 2 if args[index] in valued else 1
assert args[index] == {image!r}, args
spec = json.dumps({{"mount": mount, "labels": labels, "env": env, "command": args[index + 1:]}})
if marker("_slow_create"):
    subprocess.Popen(
        [sys.executable, "-c", {register!r}, str(os.getpid()), path(name, pending=True),
         path(name), spec, path("_hold_create"), {pids!r}],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    while not os.path.exists(path(name, pending=True)):
        time.sleep(0.01)
    time.sleep(60)
    raise SystemExit(1)
with open(path(name), "w") as stream:
    stream.write(spec)
print("0123456789ab")
"""


def calls(log: Path) -> list[list[str]]:
    return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []


def commands(log: Path) -> list[str]:
    return [call[0] for call in calls(log)]


def state_dir(log: Path) -> Path:
    return log.parent / "containers"


def containers(log: Path) -> list[str]:
    """Containers the fake daemon still has, created or being created."""
    return sorted(
        p.name.removeprefix("_pending-")
        for p in state_dir(log).iterdir()
        if p.name.startswith(("agent-eval-", "_pending-"))
    )


def daemon_marker(log: Path, name: str) -> None:
    (state_dir(log) / name).touch()


def wait_for_pending_creates(log: Path) -> None:
    """Until the daemon has registered every container whose create was in flight."""
    deadline = time.monotonic() + 10
    while any(p.name.startswith("_pending-") for p in state_dir(log).iterdir()):
        assert time.monotonic() < deadline, "a slow create was never registered"
        time.sleep(0.01)


def docker_ps(docker: Path, run_id: str = RUN_ID) -> list[str]:
    """What ``docker ps -aq --filter label=agent-eval.run=<run_id>`` lists."""
    command = [str(docker), "ps", "-aq", "--filter", f"label=agent-eval.run={run_id}"]
    return subprocess.run(command, capture_output=True, text=True, check=True).stdout.split()


def register(log: Path, name: str, run_id: str = RUN_ID) -> None:
    """A container the daemon has, as if created by an earlier attempt."""
    spec = {"mount": {"source": str(log.parent)}, "labels": [f"agent-eval.run={run_id}"]}
    (state_dir(log) / name).write_text(json.dumps(spec))


@pytest.fixture(autouse=True)
def no_real_docker(monkeypatch: pytest.MonkeyPatch) -> None:
    """No test may reach a real docker daemon: every client call must use a fake binary."""
    real = process.run_process

    async def guarded(command: list[str], *args: Any, **kwargs: Any) -> ProcessResult:
        assert command[0] != "docker", "test would call the real docker client"
        return await real(command, *args, **kwargs)

    monkeypatch.setattr(isolation, "run_process", guarded)


def leftover_registrars(pids: Path) -> list[int]:
    """Detached daemon-side processes of slow creates that are still running."""
    alive = []
    for pid_file in pids.iterdir():
        try:
            cmdline = Path(f"/proc/{pid_file.name}/cmdline").read_bytes()
        except FileNotFoundError:
            continue
        if b"os.getppid" in cmdline:
            alive.append(int(pid_file.name))
    return alive


@pytest.fixture
def fake_docker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[Path, Path]]:
    log = tmp_path / "docker-calls.jsonl"
    state = tmp_path / "containers"
    state.mkdir()
    pids = tmp_path / "registrars"
    pids.mkdir()
    path = tmp_path / "bin" / "docker"
    path.parent.mkdir()
    path.write_text(
        FAKE_DOCKER.format(
            python=sys.executable,
            log=str(log),
            state=str(state),
            image=IMAGE,
            register=REGISTER,
            pids=str(pids),
        )
    )
    path.chmod(0o755)
    monkeypatch.setattr(isolation, "CLEANUP_DELAY_S", 0.05)
    yield path, log
    # Release any hold so registrars can finish, then make sure none outlives the test.
    (state / "_hold_create").unlink(missing_ok=True)
    deadline = time.monotonic() + 5
    while leftover_registrars(pids) and time.monotonic() < deadline:
        time.sleep(0.01)
    leaked = leftover_registrars(pids)
    for pid in leaked:
        with contextlib.suppress(ProcessLookupError):
            os.kill(pid, signal.SIGKILL)
    assert not leaked, f"slow-create registrars still running: {leaked}"


def options(docker: Path, **extra: Any) -> IsolationOptions:
    return IsolationOptions(mode="docker", image=IMAGE, docker=str(docker), **extra)


def sandbox_for(docker: Path) -> Sandbox:
    return Sandbox(options(docker), RUN_ID)


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
        run_id="r1",
        env_names=["API_KEY", "LANG"],
        user="1000:1000",
    )
    assert argv[:2] == ["docker", "create"]
    # Removal is explicit after `start`, so the container cannot vanish before it is removed.
    assert "--rm" not in argv
    assert value_of(argv, "--name") == ["agent-eval-x"]
    assert value_of(argv, "--label") == ["agent-eval.attempt=agent-eval-x", "agent-eval.run=r1"]
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
        run_id="r",
        env_names=[],
    )
    assert argv[0] == "/opt/docker"
    assert value_of(argv, "--network") == ["bridge"]
    assert "--user" not in argv and "--env" not in argv


def test_docker_command_rejects_unmountable_paths(tmp_path: Path) -> None:
    workdir = tmp_path / "a,b"
    workdir.mkdir()
    with pytest.raises(ValueError, match="cannot be bind-mounted"):
        docker_command(IsolationOptions(), ["true"], workdir, name="n", run_id="r", env_names=[])


def test_container_path_rewrites_whole_components(tmp_path: Path) -> None:
    workdir = tmp_path / "w"
    assert container_path(str(workdir), workdir) == "/work"
    assert container_path(f"{workdir}/a/b.py", workdir) == "/work/a/b.py"
    assert container_path(f"--junitxml={workdir}/r.xml", workdir) == "--junitxml=/work/r.xml"
    assert container_path(f"{workdir}2/x", workdir) == f"{workdir}2/x"
    assert container_path(f"--out={workdir}2/x", workdir) == f"--out={workdir}2/x"
    assert container_path("unrelated", workdir) == "unrelated"
    # Embedded in a longer string, a path ends at whitespace or punctuation.
    assert container_path(f"cd {workdir}/a && ls {workdir}", workdir) == "cd /work/a && ls /work"


def test_container_path_converts_windows_separators() -> None:
    workdir = PureWindowsPath(r"C:\x\attempt")
    assert container_path(r"C:\x\attempt\_agent_prompt.txt", workdir) == "/work/_agent_prompt.txt"
    assert container_path(r"--out=C:\x\attempt\a\b.py", workdir) == "--out=/work/a/b.py"
    assert container_path(r"C:\x\attempt", workdir) == "/work"
    assert container_path(r"C:\x\attempt2\y", workdir) == r"C:\x\attempt2\y"
    assert container_path(r"cd C:\x\attempt\a\b && run", workdir) == "cd /work/a/b && run"
    # On POSIX hosts a backslash is part of a file name and stays.
    assert container_path("/tmp/w/a\\b", PurePosixPath("/tmp/w")) == "/work/a\\b"


@pytest.mark.parametrize(
    ("host", "expected"),
    [
        (r"C:\x\attempt\folder name\a.py", "/work/folder name/a.py"),
        (r"C:\x\attempt\it's (v2), a=b;c:d\x y.py", "/work/it's (v2), a=b;c:d/x y.py"),
        (r"--out=C:\x\attempt\my dir\r.xml", "--out=/work/my dir/r.xml"),
        (r"C:\x\attempt\a b\\", "/work/a b//"),
    ],
)
def test_container_path_windows_names_with_spaces_and_punctuation(host: str, expected: str) -> None:
    assert container_path(host, PureWindowsPath(r"C:\x\attempt")) == expected


@pytest.mark.parametrize(
    ("host", "expected"),
    [
        ("/tmp/w/folder name/a.py", "/work/folder name/a.py"),
        ("/tmp/w/it's (v2), a=b;c:d\\e/x y.py", "/work/it's (v2), a=b;c:d\\e/x y.py"),
        ("--out=/tmp/w/my dir/r.xml", "--out=/work/my dir/r.xml"),
        ("/tmp/w2/folder name/a.py", "/tmp/w2/folder name/a.py"),
    ],
)
def test_container_path_posix_names_with_spaces_and_punctuation(host: str, expected: str) -> None:
    assert container_path(host, PurePosixPath("/tmp/w")) == expected


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
        {"memory": "0"},
        {"memory": "0g"},
        {"memory": "0.0m"},
        {"memory": "000B"},
        # docker truncates fractional bytes: 0.5b would be 0, which docker reads as no limit.
        {"memory": "0.5b"},
        # Below docker's 6 MiB minimum.
        {"memory": "1b"},
        {"memory": "1023k"},
        {"memory": "6291455"},
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


@pytest.mark.parametrize("memory", ["0.5g", "6m", "0.01g", "2g", "6291456", "6144K", "10.0G"])
def test_memory_limits_of_at_least_6m_are_valid(memory: str) -> None:
    assert IsolationOptions(memory=memory).memory == memory


@pytest.mark.parametrize(
    ("memory", "expected"),
    [("0.5b", 0), ("1023k", 1047552), ("6M", 6291456), ("0.01g", 10737418), ("6291456", 6291456)],
)
def test_memory_bytes_truncates_like_docker(memory: str, expected: int) -> None:
    assert isolation.memory_bytes(memory) == expected


def test_memory_bytes_rejects_malformed_values() -> None:
    with pytest.raises(ValueError, match="invalid memory limit"):
        isolation.memory_bytes("1.5x")


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
    code = main(["run", str(config_path), "--out", str(out), "--isolation", "local"])
    assert code == 0
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
    code = main(["run", str(config_path), "--out", str(out), "--isolation", "docker"])
    assert code == 0
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
    reason = asyncio.run(probe_docker(options(failing)))
    assert reason == "docker daemon is unreachable"
    reason = asyncio.run(probe_docker(options(silent)))
    assert reason == "docker daemon is unreachable"
    monkeypatch.setattr(isolation, "PROBE_TIMEOUT_S", 0.3)
    reason = asyncio.run(probe_docker(options(slow)))
    assert reason == "docker daemon did not answer within 0.3 s"
    sandbox, record = asyncio.run(select_isolation(options(failing), RUN_ID))
    assert sandbox is None and record.used == "local"


def test_grading_in_docker(fake_docker: tuple[Path, Path], task_path: Path, workdir: Path) -> None:
    docker, log = fake_docker
    sandbox, record = asyncio.run(select_isolation(options(docker), RUN_ID))
    assert sandbox is not None and sandbox.run_id == RUN_ID
    assert record.model_dump() == {"requested": "docker", "used": "docker", "warning": None}
    task = load_task(task_path)
    (workdir / "solution.py").write_text("def answer():\n    return 42\n")
    result = asyncio.run(grade(task, task_path, workdir, sandbox))
    assert (result.outcome, result.passed, result.total) == ("pass", 1, 1)
    version, create, start, rm = calls(log)
    assert version == ["version", "--format", "{{.Server.Version}}"]
    (name,) = value_of(create, "--name")
    assert (start, rm) == (["start", "--attach", name], ["rm", "--force", name])
    inner = create[create.index(IMAGE) + 1 :]
    assert inner[:2] == ["python", "-I"]
    assert value_of(inner, "-c")[1] == "/dev/null"
    assert "--rootdir" in inner and inner[inner.index("--rootdir") + 1] == "/work"
    assert any(part.startswith("--junitxml=/work/_hidden_") for part in inner)
    assert str(workdir) not in json.dumps(inner)
    assert set(value_of(create, "--env")) >= {"PYTEST_DISABLE_PLUGIN_AUTOLOAD", "HOME", "TMPDIR"}
    assert "PATH" not in value_of(create, "--env")
    assert containers(log) == []


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
    runner.sandbox = sandbox_for(docker)
    generation = asyncio.run(runner.generate(load_task(task_path), workdir))
    assert "agent done" in generation.raw_output
    assert "321-eulav-terc3s" in generation.raw_output
    assert (workdir / "solution.py").is_file()
    create, start, rm = calls(log)
    assert "AGENT_SECRET" in value_of(create, "--env")
    assert "s3cret-value-123" not in json.dumps(calls(log))
    assert create[-2:] == ["/work/_agent_prompt.txt", "/work"]
    assert (start[0], rm[0]) == ("start", "rm")


SLEEP = [sys.executable, "-c", "import time; time.sleep(30)"]


def test_create_finishes_before_start_and_a_clean_exit_is_removed(
    fake_docker: tuple[Path, Path], workdir: Path
) -> None:
    docker, log = fake_docker
    command = [sys.executable, "-c", "print('hi')"]
    result = asyncio.run(sandbox_for(docker).run(command, workdir, 30, {}))
    assert (result.returncode, result.timed_out) == (0, False)
    # The container ID printed by `create` is not part of the attempt's output.
    assert result.output == "hi\n"
    create, start, rm = calls(log)
    (name,) = value_of(create, "--name")
    assert create[0] == "create"
    assert (start, rm) == (["start", "--attach", name], ["rm", "--force", name])
    assert containers(log) == []


def test_containers_carry_attempt_and_run_labels(tmp_path: Path) -> None:
    argv = docker_command(
        IsolationOptions(), ["true"], tmp_path, name="n", run_id="r", env_names=[]
    )
    assert value_of(argv, "--label") == ["agent-eval.attempt=n", "agent-eval.run=r"]


def test_timeout_removes_the_container(fake_docker: tuple[Path, Path], workdir: Path) -> None:
    docker, log = fake_docker
    result = asyncio.run(sandbox_for(docker).run(SLEEP, workdir, 0.5, {}))
    assert result.timed_out
    assert "could not be removed" not in result.output
    create, start, rm = calls(log)
    (name,) = value_of(create, "--name")
    assert (start[0], rm) == ("start", ["rm", "--force", name])
    assert containers(log) == []


def test_non_zero_exit_removes_the_container(fake_docker: tuple[Path, Path], workdir: Path) -> None:
    docker, log = fake_docker
    command = [sys.executable, "-c", "print('boom'); raise SystemExit(3)"]
    result = asyncio.run(sandbox_for(docker).run(command, workdir, 30, {}))
    assert (result.returncode, result.timed_out) == (3, False)
    assert "boom" in result.output and "could not be removed" not in result.output
    assert commands(log) == ["create", "start", "rm"]
    assert containers(log) == []


def test_cancellation_while_running_removes_the_container(
    fake_docker: tuple[Path, Path], workdir: Path
) -> None:
    docker, log = fake_docker
    sandbox = sandbox_for(docker)

    async def cancel_while_running() -> bool:
        task = asyncio.create_task(sandbox.run(SLEEP, workdir, 30, {}))
        while "start" not in commands(log):
            await asyncio.sleep(0.05)
        await asyncio.sleep(0.2)
        task.cancel()
        await asyncio.wait([task])
        return task.cancelled()

    cancelled = asyncio.run(cancel_while_running())
    assert cancelled
    create, _, rm = calls(log)
    assert rm == ["rm", "--force", *value_of(create, "--name")]
    assert containers(log) == []


def test_cleanup_is_not_cancellable(fake_docker: tuple[Path, Path], tmp_path: Path) -> None:
    docker, log = fake_docker
    daemon_marker(log, "_slow_rm")
    sandbox = sandbox_for(docker)
    started = state_dir(log) / "_rm_started"

    async def cancel_during_cleanup() -> tuple[bool, list[str], bool]:
        # Like the engine: the workdir is released only once the attempt has ended.
        with tempfile.TemporaryDirectory(dir=tmp_path) as directory:
            task = asyncio.create_task(
                sandbox.run([sys.executable, "-c", ""], Path(directory), 30, {})
            )
            while not started.exists():
                await asyncio.sleep(0.01)
            task.cancel()
            await asyncio.sleep(0.05)
            task.cancel()
            await asyncio.wait([task])
            # What the daemon has at the moment the cancellation reached the caller.
            left = containers(log)
            return task.cancelled(), left, Path(directory).is_dir()

    cancelled, left, workdir_kept = asyncio.run(cancel_during_cleanup())
    assert cancelled and workdir_kept
    assert left == []
    assert commands(log) == ["create", "start", "rm"]
    assert (state_dir(log) / "_rm_saw_workdir").read_text() == "True"


def test_uncancellable_returns_the_result() -> None:
    async def value() -> int:
        await asyncio.sleep(0)
        return 7

    returned = asyncio.run(isolation.uncancellable(value()))
    assert returned == 7


def test_create_failure_is_returned_without_start(
    fake_docker: tuple[Path, Path], workdir: Path
) -> None:
    docker, log = fake_docker
    daemon_marker(log, "_create_fails")
    result = asyncio.run(sandbox_for(docker).run(["true"], workdir, 30, {}))
    assert (result.returncode, result.timed_out) == (125, False)
    assert "Unable to find image" in result.output
    assert commands(log) == ["create"]


def test_missing_client_raises_before_any_container(tmp_path: Path) -> None:
    sandbox = Sandbox(options(tmp_path / "missing"), RUN_ID)
    with pytest.raises(OSError):
        asyncio.run(sandbox.run(["true"], tmp_path, 5, {}))


def test_sweep_removes_a_container_created_after_the_client_was_killed(
    fake_docker: tuple[Path, Path], workdir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    docker, log = fake_docker
    # The client is killed mid-create; the daemon registers the container only afterwards.
    daemon_marker(log, "_slow_create")
    sandbox = sandbox_for(docker)
    result = asyncio.run(sandbox.run(SLEEP, workdir, 0.5, {}))
    assert result.timed_out
    assert commands(log) == ["create"]
    (name,) = containers(log)
    # docker ps does not wait for creates in flight: the container is visible once registered.
    wait_for_pending_creates(log)
    register(log, "agent-eval-other-run", run_id="other")
    failed = asyncio.run(sandbox.sweep())
    assert failed == 0
    assert containers(log) == ["agent-eval-other-run"]
    assert calls(log)[1:] == [
        ["ps", "-aq", "--filter", f"label=agent-eval.run={RUN_ID}"],
        ["rm", "--force", name],
    ]
    assert "1 container(s) of this run were left over and were removed" in capsys.readouterr().err


def test_a_create_completing_after_the_sweep_leaves_a_container_never_started(
    fake_docker: tuple[Path, Path], workdir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The documented residual: the sweep cannot remove what the daemon has not registered
    yet. The container stays, findable by its run label, and was never started."""
    docker, log = fake_docker
    daemon_marker(log, "_slow_create")
    daemon_marker(log, "_hold_create")
    sandbox = sandbox_for(docker)
    result = asyncio.run(sandbox.run(SLEEP, workdir, 0.5, {}))
    assert result.timed_out
    failed = asyncio.run(sandbox.sweep())
    assert failed == 0
    assert capsys.readouterr().err == ""
    # The daemon finishes the create only now.
    (state_dir(log) / "_hold_create").unlink()
    wait_for_pending_creates(log)
    (name,) = containers(log)
    listed = docker_ps(docker)
    assert listed == [name]
    assert commands(log) == ["create", "ps", "ps"]
    assert all(call[0] != "start" for call in calls(log))


def test_sweep_with_nothing_left_is_silent(
    fake_docker: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    docker, log = fake_docker
    failed = asyncio.run(sandbox_for(docker).sweep())
    assert failed == 0
    assert commands(log) == ["ps"]
    assert capsys.readouterr().err == ""


def test_sweep_reports_containers_it_cannot_remove(
    fake_docker: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    docker, log = fake_docker
    register(log, "agent-eval-a")
    register(log, "agent-eval-b")
    daemon_marker(log, "_stuck")
    failed = asyncio.run(sandbox_for(docker).sweep())
    assert failed == 2
    err = capsys.readouterr().err
    assert "2 container(s) of this run were left over; 2 could not be removed" in err
    assert f"docker ps -a --filter label=agent-eval.run={RUN_ID}" in err
    assert containers(log) == ["agent-eval-a", "agent-eval-b"]


def test_sweep_reports_when_it_cannot_list(
    fake_docker: tuple[Path, Path], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    docker, log = fake_docker
    daemon_marker(log, "_ps_fails")
    failed = asyncio.run(sandbox_for(docker).sweep())
    assert failed == 0
    failed = asyncio.run(Sandbox(options(tmp_path / "missing"), RUN_ID).sweep())
    assert failed == 0
    err = capsys.readouterr().err
    assert err.count("could not list the containers left by this run") == 2
    assert f"docker ps -a --filter label=agent-eval.run={RUN_ID}" in err


def test_cleanup_failure_is_reported_without_masking_the_result(
    fake_docker: tuple[Path, Path], workdir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    docker, log = fake_docker
    daemon_marker(log, "_stuck")
    sandbox = sandbox_for(docker)
    result = asyncio.run(sandbox.run(SLEEP, workdir, 0.5, {}))
    (name,) = containers(log)
    assert result.timed_out
    assert result.output.endswith(f"[agent-eval: container {name} could not be removed]\n")
    assert f"container {name} could not be removed" in capsys.readouterr().err
    assert commands(log).count("rm") == isolation.CLEANUP_ROUNDS

    command = [sys.executable, "-c", "raise SystemExit(4)"]
    result = asyncio.run(sandbox.run(command, workdir, 30, {}))
    assert (result.returncode, result.timed_out) == (4, False)
    assert "could not be removed" in result.output


def test_cleanup_is_bounded_in_time(
    fake_docker: tuple[Path, Path], workdir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    docker, log = fake_docker
    register(log, "agent-eval-x")
    daemon_marker(log, "_stuck")
    monkeypatch.setattr(isolation, "CLEANUP_DELAY_S", 10.0)
    monkeypatch.setattr(isolation, "CLEANUP_BUDGET_S", 0.5)
    sandbox = sandbox_for(docker)

    async def timed() -> tuple[bool, float]:
        loop = asyncio.get_running_loop()
        start = loop.time()
        removed = await sandbox.remove("agent-eval-x", workdir)
        return removed, loop.time() - start

    removed, elapsed = asyncio.run(timed())
    assert not removed and elapsed < 5.0
    assert calls(log) == [["rm", "--force", "agent-eval-x"]]


def test_removal_of_an_unknown_container_succeeds(
    fake_docker: tuple[Path, Path], workdir: Path
) -> None:
    docker, log = fake_docker
    removed = asyncio.run(sandbox_for(docker).remove("agent-eval-gone", workdir))
    assert removed
    assert commands(log) == ["rm"]


def agent_config(config_path: Path, docker: Path) -> None:
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


def test_engine_runs_attempts_in_containers(
    fake_docker: tuple[Path, Path], config_path: Path, tmp_path: Path
) -> None:
    docker, log = fake_docker
    agent_config(config_path, docker)
    attempts = asyncio.run(run_config(config_path, tmp_path / "run"))
    assert {(a.model, a.outcome) for a in attempts} == {
        ("correct", "pass"),
        ("wrong", "fail"),
        ("agent", "pass"),
    }
    assert all(a.isolation is not None and a.isolation.used == "docker" for a in attempts)
    invocations = calls(log)
    names = commands(log)
    assert names.count("version") == 1
    creates = [c for c in invocations if c[0] == "create"]
    # Six gradings plus two agent generations, each in its own container.
    assert len(creates) == names.count("start") == names.count("rm") == 8
    assert len({value_of(c, "--name")[0] for c in creates}) == 8
    run_labels = {label for c in creates for label in value_of(c, "--label")} - {
        f"agent-eval.attempt={value_of(c, '--name')[0]}" for c in creates
    }
    (run_label,) = run_labels
    # One sweep for the run's label, after every attempt.
    assert invocations[-1] == ["ps", "-aq", "--filter", f"label={run_label}"]
    assert containers(log) == []


def test_engine_sweeps_after_cancellation(
    fake_docker: tuple[Path, Path],
    config_path: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docker, log = fake_docker
    agent_config(config_path, docker)
    # One attempt at a time, so the create in flight is the one the test has seen start.
    data = yaml.safe_load(config_path.read_text())
    data["concurrency"] = 1
    config_path.write_text(yaml.safe_dump(data))
    # Every create hangs and the daemon creates the container after the client is killed.
    daemon_marker(log, "_slow_create")
    sweep = Sandbox.sweep

    async def sweep_once_registered(self: Sandbox) -> int:
        # docker ps does not wait for creates in flight: hold the sweep until the daemon has
        # registered the killed create's container, so the sweep is sure to see it.
        await asyncio.to_thread(wait_for_pending_creates, log)
        return await sweep(self)

    monkeypatch.setattr(Sandbox, "sweep", sweep_once_registered)

    async def interrupted() -> bool:
        task = asyncio.create_task(run_config(config_path, tmp_path / "run"))
        while not containers(log):
            await asyncio.sleep(0.05)
        task.cancel()
        await asyncio.wait([task])
        return task.cancelled()

    cancelled = asyncio.run(interrupted())
    assert cancelled
    assert containers(log) == []
    names = commands(log)
    assert names[-1] == "rm" and "ps" in names and "start" not in names
    assert "were left over and were removed" in capsys.readouterr().err


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
    code = main(["report", str(out / "results.jsonl")])
    assert code == 0


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
    config_path: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def unavailable(options: IsolationOptions) -> str | None:
        return "docker daemon is unreachable"

    monkeypatch.setattr(isolation, "probe_docker", unavailable)
    out = tmp_path / "run"
    # Docker is unavailable, so attempts fall back, but docker was what the run asked for.
    code = main(["run", str(config_path), "--out", str(out), "--isolation", "docker"])
    assert code == 0
    assert "isolation unavailable (docker daemon is unreachable)" in capsys.readouterr().err
    resolved = yaml.safe_load((out / "config.resolved.yaml").read_text())
    assert resolved["isolation"]["mode"] == "docker"
    interrupt(out)
    code = main(["run", str(config_path), "--out", str(out), "--resume"])
    assert code == 2
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
    attempts = asyncio.run(run_config(config_path, out, resume=True))
    assert len(attempts) == 4
    interrupt(out)
    attempts = asyncio.run(run_config(config_path, out, resume=True, isolation="local"))
    assert len(attempts) == 4
    interrupt(out)
    # Absent means local, so resuming it in docker is a different config.
    docker_config(config_path, docker)
    with pytest.raises(ValueError, match=r"isolation local, now docker"):
        asyncio.run(run_config(config_path, out, resume=True, isolation="docker"))
