"""Container-per-attempt isolation: ``docker run`` argv, availability probe and fallback."""

from __future__ import annotations

import asyncio
import contextlib
import os
import re
import sys
import uuid
from dataclasses import dataclass, replace
from pathlib import Path, PurePath
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from agent_eval.process import ProcessResult, run_process

IsolationMode = Literal["local", "docker"]

CONTAINER_WORKDIR = "/work"
TMPFS = "/tmp:rw,nosuid,nodev,size=256m"
PROBE_TIMEOUT_S = 10.0
# Removing a container after a non-clean end: a few rounds of ``rm --force`` + ``inspect``.
CLEANUP_ROUNDS = 5
CLEANUP_DELAY_S = 0.5
CLEANUP_BUDGET_S = 20.0
LABEL = "agent-eval.attempt"
# The docker client needs these to find its binary and daemon; they are not sent to containers.
CLIENT_ENV = (
    "PATH",
    "SYSTEMROOT",
    "DOCKER_HOST",
    "DOCKER_CONTEXT",
    "DOCKER_CONFIG",
    "DOCKER_CERT_PATH",
    "DOCKER_TLS_VERIFY",
)
# Host paths that mean nothing inside the container; the image's PATH and a tmpfs HOME win.
HOST_ONLY_ENV = {
    "PATH",
    "SYSTEMROOT",
    "HOME",
    "TMPDIR",
    "XDG_CONFIG_HOME",
    "XDG_CACHE_HOME",
    "XDG_DATA_HOME",
}
CONTAINER_ENV = {"HOME": "/tmp", "TMPDIR": "/tmp"}


class _StrictModel(BaseModel):
    # specs.StrictModel, repeated because specs imports this module for the run config.
    model_config = ConfigDict(extra="forbid")


class IsolationOptions(_StrictModel):
    mode: IsolationMode = "local"
    image: str = Field(default="python:3.12-slim", pattern=r"^[^-\s]\S*$")
    # No network unless the config opts into docker's default bridge.
    network: Literal["none", "bridge"] = "none"
    memory: str = Field(default="2g", pattern=r"^[0-9]+(\.[0-9]+)?[bkmgBKMG]?$")
    cpus: Annotated[float, Field(gt=0, allow_inf_nan=False)] = 2.0
    pids_limit: int = Field(default=256, ge=1, strict=True)
    docker: str = Field(default="docker", min_length=1)


class IsolationRecord(_StrictModel):
    """What an attempt asked for and what it actually ran under."""

    requested: IsolationMode
    used: IsolationMode
    warning: str | None = None


def host_user() -> str | None:
    """``uid:gid`` of the harness, so files written to the bind mount stay the user's."""
    if os.name != "posix":
        return None
    return f"{os.getuid()}:{os.getgid()}"


def container_path(value: str, workdir: PurePath) -> str:
    """Rewrite every occurrence of the host workdir in ``value`` to the container mount."""
    roots = {str(workdir)}
    if isinstance(workdir, Path):
        roots.add(str(workdir.resolve()))
    pattern = "|".join(re.escape(root) for root in sorted(roots, key=len, reverse=True))

    def rewrite(match: re.Match[str]) -> str:
        rest = match["rest"]
        # The container is Linux: the remainder of a Windows host path needs forward slashes.
        return CONTAINER_WORKDIR + (rest.replace("\\", "/") if "\\" in match["root"] else rest)

    # Only whole path components: /tmp/w must not match inside /tmp/w2.
    return re.sub(
        f"(?P<root>{pattern})(?P<rest>[/\\\\][^\\s\"'=:;,)]*|)(?=[\\s\"'=:;,)]|$)",
        rewrite,
        value,
    )


def docker_command(
    options: IsolationOptions,
    command: list[str],
    workdir: Path,
    *,
    name: str,
    env_names: list[str],
    user: str | None = None,
) -> list[str]:
    """``docker run`` argv for one attempt. Environment values are never in the argv: each
    ``--env NAME`` makes the docker client copy the value from its own environment."""
    source = str(workdir.resolve())
    if "," in source or '"' in source:
        raise ValueError(f"workdir path cannot be bind-mounted: {source}")
    argv = [
        options.docker,
        "run",
        "--rm",
        "--name",
        name,
        "--label",
        f"{LABEL}={name}",
        "--network",
        options.network,
        "--memory",
        options.memory,
        "--memory-swap",
        options.memory,
        "--cpus",
        f"{options.cpus:g}",
        "--pids-limit",
        str(options.pids_limit),
        "--read-only",
        "--tmpfs",
        TMPFS,
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
    ]
    if user is not None:
        argv += ["--user", user]
    argv += [
        "--mount",
        f"type=bind,source={source},target={CONTAINER_WORKDIR}",
        "--workdir",
        CONTAINER_WORKDIR,
        # Run the command itself, not an image entrypoint such as the harness's agent-eval.
        "--entrypoint",
        "",
    ]
    for env_name in env_names:
        argv += ["--env", env_name]
    return [*argv, options.image, *(container_path(part, workdir) for part in command)]


def client_environment() -> dict[str, str]:
    env = {name: os.environ[name] for name in CLIENT_ENV if name in os.environ}
    # The client sees the container's HOME, so point it at the host's docker config.
    if "DOCKER_CONFIG" not in env:
        with contextlib.suppress(RuntimeError):
            env["DOCKER_CONFIG"] = str(Path.home() / ".docker")
    return env


@dataclass(frozen=True)
class Sandbox:
    """Runs each command in a fresh container with the workdir mounted at /work."""

    options: IsolationOptions

    async def run(
        self, command: list[str], workdir: Path, timeout_s: float, env: dict[str, str]
    ) -> ProcessResult:
        """Like ``run_process``. After any end other than a clean exit the container is
        removed as well; if that fails the output says so, the outcome is kept."""
        inner = {k: v for k, v in env.items() if k not in HOST_ONLY_ENV} | CONTAINER_ENV
        client = client_environment()
        env_names = [name for name in inner if name not in client]
        name = f"agent-eval-{uuid.uuid4().hex}"
        argv = docker_command(
            self.options, command, workdir, name=name, env_names=env_names, user=host_user()
        )
        try:
            result = await run_process(argv, workdir, timeout_s, inner | client)
        except (asyncio.CancelledError, OSError):
            # The client may die before the daemon has created or started the container.
            await self.remove(name, workdir, settle=True)
            raise
        # A client that exited on its own saw the container end, so there is no startup race.
        unclean = result.timed_out or result.returncode != 0
        if unclean and not await self.remove(name, workdir, settle=result.timed_out):
            note = f"\n[agent-eval: container {name} could not be removed]\n"
            result = replace(result, output=result.output + note)
        return result

    async def remove(self, name: str, cwd: Path, *, settle: bool) -> bool:
        """``docker rm --force`` (which also kills) until ``inspect`` finds no container.

        With ``settle``, the container must be absent in two rounds a delay apart, so one
        the daemon creates after the first check is still removed. False, after logging to
        stderr, if it may still exist when the rounds or the time budget run out."""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + CLEANUP_BUDGET_S
        needed = 2 if settle else 1
        absent = 0
        for round_ in range(CLEANUP_ROUNDS):
            remaining = deadline - loop.time()
            if remaining <= 0:
                break
            if round_:
                await asyncio.sleep(min(CLEANUP_DELAY_S, remaining))
            if await self._docker(["rm", "--force", name], cwd, deadline) is None:
                absent = 0
                continue
            inspected = await self._docker(["container", "inspect", name], cwd, deadline)
            gone = inspected is not None and "no such" in inspected.output.lower()
            absent = absent + 1 if gone else 0
            if absent >= needed:
                return True
        print(f"agent-eval: warning: container {name} could not be removed", file=sys.stderr)
        return False

    async def _docker(self, args: list[str], cwd: Path, deadline: float) -> ProcessResult | None:
        """One docker client call within the cleanup budget; None if it could not run."""
        remaining = deadline - asyncio.get_running_loop().time()
        if remaining <= 0:
            return None
        try:
            result = await run_process(
                [self.options.docker, *args], cwd, remaining, client_environment()
            )
        except OSError:
            return None
        return None if result.timed_out else result


async def probe_docker(options: IsolationOptions) -> str | None:
    """None if the docker daemon answers, otherwise why it cannot be used."""
    command = [options.docker, "version", "--format", "{{.Server.Version}}"]
    try:
        result = await run_process(command, Path.cwd(), PROBE_TIMEOUT_S, client_environment())
    except OSError:
        return f"docker executable not found: {options.docker}"
    if result.timed_out:
        return f"docker daemon did not answer within {PROBE_TIMEOUT_S:g} s"
    if result.returncode or not result.output.strip():
        return "docker daemon is unreachable"
    return None


async def select_isolation(options: IsolationOptions) -> tuple[Sandbox | None, IsolationRecord]:
    """The sandbox to use, or None for the local runner, plus the record for each attempt."""
    if options.mode == "local":
        return None, IsolationRecord(requested="local", used="local")
    reason = await probe_docker(options)
    if reason is None:
        return Sandbox(options), IsolationRecord(requested="docker", used="docker")
    warning = f"docker isolation unavailable ({reason}); attempts ran with the local runner"
    return None, IsolationRecord(requested="docker", used="local", warning=warning)
