"""Container-per-attempt isolation: ``docker create`` argv, availability probe and fallback."""

from __future__ import annotations

import asyncio
import contextlib
import os
import re
import sys
import uuid
from collections.abc import Coroutine
from dataclasses import dataclass, replace
from pathlib import Path, PurePath
from typing import Annotated, Any, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from agent_eval.process import ProcessResult, run_process

IsolationMode = Literal["local", "docker"]

CONTAINER_WORKDIR = "/work"
TMPFS = "/tmp:rw,nosuid,nodev,size=256m"
PROBE_TIMEOUT_S = 10.0
# Removing a container: ``rm --force``, retried a few times within a time budget.
CLEANUP_ROUNDS = 5
CLEANUP_DELAY_S = 0.5
CLEANUP_BUDGET_S = 20.0
LABEL = "agent-eval.attempt"
# Every container of one run, so the end-of-run sweep finds those an attempt could not remove.
RUN_LABEL = "agent-eval.run"
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

T = TypeVar("T")


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

    @field_validator("memory")
    @classmethod
    def _memory_positive(cls, value: str) -> str:
        # docker reads 0 as "no limit".
        if float(value.rstrip("bkmgBKMG")) == 0:
            raise ValueError("memory must be greater than zero")
        return value


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

    # A whole argument, or an --option=value, that is a path under the workdir: everything
    # after the root is the path, spaces and punctuation in folder names included.
    whole = re.fullmatch(
        f"(?P<option>-[^=\\s]*=)?(?P<root>{pattern})(?P<rest>[/\\\\].*|)", value, re.S
    )
    if whole:
        return (whole["option"] or "") + rewrite(whole)
    # Embedded in a longer string, the path ends at whitespace, a quote or punctuation. Only
    # whole path components: /tmp/w must not match inside /tmp/w2.
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
    run_id: str,
    env_names: list[str],
    user: str | None = None,
) -> list[str]:
    """``docker create`` argv for one attempt. Environment values are never in the argv: each
    ``--env NAME`` makes the docker client copy the value from its own environment."""
    source = str(workdir.resolve())
    if "," in source or '"' in source:
        raise ValueError(f"workdir path cannot be bind-mounted: {source}")
    argv = [
        options.docker,
        "create",
        "--name",
        name,
        "--label",
        f"{LABEL}={name}",
        "--label",
        f"{RUN_LABEL}={run_id}",
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


async def uncancellable(coro: Coroutine[Any, Any, T]) -> T:
    """Run ``coro`` to completion even if the caller is cancelled meanwhile, any number of
    times; the cancellation is re-raised once it has finished."""
    task = asyncio.ensure_future(coro)
    cancelled: asyncio.CancelledError | None = None
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError as exc:
            cancelled = exc
    if cancelled is not None:
        raise cancelled
    return task.result()


@dataclass(frozen=True)
class Sandbox:
    """Runs each command in a fresh container with the workdir mounted at /work. Every
    container is labelled with ``run_id``, so ``sweep`` can find what attempts left behind."""

    options: IsolationOptions
    run_id: str

    async def run(
        self, command: list[str], workdir: Path, timeout_s: float, env: dict[str, str]
    ) -> ProcessResult:
        """Like ``run_process``. ``docker create`` must finish before ``docker start --attach``
        runs the command, so once it has started the container is known to exist and is
        always removed before this returns or raises. If removal fails the output says so,
        the outcome is kept. A ``create`` interrupted in flight is left to ``sweep``."""
        inner = {k: v for k, v in env.items() if k not in HOST_ONLY_ENV} | CONTAINER_ENV
        client = client_environment()
        env_names = [name for name in inner if name not in client]
        name = f"agent-eval-{uuid.uuid4().hex}"
        argv = docker_command(
            self.options,
            command,
            workdir,
            name=name,
            run_id=self.run_id,
            env_names=env_names,
            user=host_user(),
        )
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout_s
        # Creating may pull the image, which counts against the timeout.
        created = await run_process(argv, workdir, timeout_s, inner | client)
        if created.timed_out or created.returncode != 0:
            return created
        start = [self.options.docker, "start", "--attach", name]
        try:
            result = await run_process(start, workdir, max(deadline - loop.time(), 0), client)
        except BaseException:
            await uncancellable(self.remove(name, workdir))
            raise
        if not await uncancellable(self.remove(name, workdir)):
            note = f"\n[agent-eval: container {name} could not be removed]\n"
            result = replace(result, output=result.output + note)
        return result

    async def remove(self, name: str, cwd: Path) -> bool:
        """``docker rm --force`` (which also kills) a container known to have been created.

        Done once docker removes it or no longer knows it; other failures are retried within
        the rounds and time budget. False, after logging to stderr, if it may still exist."""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + CLEANUP_BUDGET_S
        for round_ in range(CLEANUP_ROUNDS):
            remaining = deadline - loop.time()
            if remaining <= 0:
                break
            if round_:
                await asyncio.sleep(min(CLEANUP_DELAY_S, remaining))
            result = await self._docker(["rm", "--force", name], cwd, deadline)
            if result is not None and (
                result.returncode == 0 or "no such container" in result.output.lower()
            ):
                return True
        print(f"agent-eval: warning: container {name} could not be removed", file=sys.stderr)
        return False

    async def sweep(self) -> int:
        """Remove every container of this run that still exists, such as one whose ``create``
        was interrupted while the daemon carried on. Not cancellable. Warns on stderr if it
        found any or could not list or remove them; returns how many it could not remove."""
        return await uncancellable(self._sweep())

    async def _sweep(self) -> int:
        label = f"{RUN_LABEL}={self.run_id}"
        hint = f"find them with: docker ps -a --filter label={label}"
        cwd = Path.cwd()
        deadline = asyncio.get_running_loop().time() + CLEANUP_BUDGET_S
        listed = await self._docker(["ps", "-aq", "--filter", f"label={label}"], cwd, deadline)
        if listed is None or listed.returncode != 0:
            print(
                f"agent-eval: warning: could not list the containers left by this run; {hint}",
                file=sys.stderr,
            )
            return 0
        found = listed.output.split()
        if not found:
            return 0
        removed = await asyncio.gather(*(self.remove(name, cwd) for name in found))
        failed = removed.count(False)
        message = f"agent-eval: warning: {len(found)} container(s) of this run were left over"
        message += f"; {failed} could not be removed, {hint}" if failed else " and were removed"
        print(message, file=sys.stderr)
        return failed

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


async def select_isolation(
    options: IsolationOptions, run_id: str
) -> tuple[Sandbox | None, IsolationRecord]:
    """The sandbox to use, or None for the local runner, plus the record for each attempt.
    ``run_id`` labels the run's containers; it must be unique per run."""
    if options.mode == "local":
        return None, IsolationRecord(requested="local", used="local")
    reason = await probe_docker(options)
    if reason is None:
        return Sandbox(options, run_id), IsolationRecord(requested="docker", used="docker")
    warning = f"docker isolation unavailable ({reason}); attempts ran with the local runner"
    return None, IsolationRecord(requested="docker", used="local", warning=warning)
