"""Jittered exponential backoff for transient provider errors, with every retry recorded."""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

_T = TypeVar("_T")


class _StrictModel(BaseModel):
    # specs.StrictModel, repeated because specs imports this module for the run config.
    model_config = ConfigDict(extra="forbid")


class RetryPolicy(_StrictModel):
    max_retries: int = Field(default=3, ge=0, le=10, strict=True)
    base_delay_s: float = Field(default=1.0, ge=0, allow_inf_nan=False)
    # The cap: no single wait, including one asked for by Retry-After, is longer.
    max_delay_s: float = Field(default=30.0, ge=0, allow_inf_nan=False)
    multiplier: float = Field(default=2.0, ge=1, le=10, allow_inf_nan=False)
    # "full" waits uniformly between 0 and the exponential delay; "none" is deterministic.
    jitter: Literal["full", "none"] = "full"


@dataclass(frozen=True)
class Transient:
    """A failure worth retrying: a short, safe reason and an optional server-requested wait."""

    reason: str
    retry_after_s: float | None = None


class RetryError(Exception):
    """The last failure of a call, with the reasons of the retries made before it."""

    def __init__(self, error: Exception, reasons: list[str]) -> None:
        super().__init__(str(error))
        self.error = error
        self.reasons = reasons


def resolve_policy(
    base: RetryPolicy,
    override: RetryPolicy | None = None,
    *,
    max_retries: int | None = None,
) -> RetryPolicy:
    """Config ``retry:`` block, then the fields a model sets itself, then ``--max-retries``."""
    values: dict[str, Any] = base.model_dump()
    if override is not None:
        values.update(override.model_dump(include=override.model_fields_set))
    if max_retries is not None:
        values["max_retries"] = max_retries
    return RetryPolicy.model_validate(values)


def delay_for(attempt: int, policy: RetryPolicy, rng: random.Random) -> float:
    """Wait before retry ``attempt`` (0-based): up to min(cap, base * multiplier**attempt)."""
    ceiling = min(policy.max_delay_s, policy.base_delay_s * policy.multiplier**attempt)
    return rng.uniform(0, ceiling) if policy.jitter == "full" else ceiling


def backoff_delays(policy: RetryPolicy, rng: random.Random) -> list[float]:
    return [delay_for(attempt, policy, rng) for attempt in range(policy.max_retries)]


async def with_retries(
    call: Callable[[], Awaitable[_T]],
    policy: RetryPolicy,
    *,
    classify: Callable[[Exception], Transient | None],
    sleep: Callable[[float], Awaitable[object]] = asyncio.sleep,
    rng: random.Random | None = None,
) -> tuple[_T, list[str]]:
    """Return ``call()``'s result and the reasons of the retries it took. Any failure that is
    not transient, or that remains after ``max_retries``, is raised as a RetryError."""
    rng = rng or random.Random()
    reasons: list[str] = []
    while True:
        try:
            return await call(), reasons
        except Exception as exc:
            transient = classify(exc)
            if transient is None or len(reasons) >= policy.max_retries:
                raise RetryError(exc, reasons) from exc
            delay = delay_for(len(reasons), policy, rng)
            if transient.retry_after_s is not None:
                delay = min(policy.max_delay_s, transient.retry_after_s)
            reasons.append(transient.reason)
            await sleep(delay)
