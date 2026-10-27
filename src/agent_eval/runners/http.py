"""Small vendor adapters with injectable transports and no SDK dependencies."""

from __future__ import annotations

import asyncio
import math
import os
import random
import re
import time
from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from pathlib import Path
from typing import Any, Literal

import httpx
from pydantic import Field

from agent_eval.retry import RetryError, RetryPolicy, Transient, with_retries
from agent_eval.runners.base import (
    Generation,
    RunnerError,
    extract_code,
    generation_prompt,
    starter_source,
)
from agent_eval.specs import PositiveSeconds, StrictModel, TaskSpec

# Rate limits, overload and gateway failures; other 4xx mean the request itself is wrong.
TRANSIENT_STATUS = frozenset({408, 409, 425, 429, 500, 502, 503, 504, 529})
# Connection-level failures. WriteTimeout is excluded: the request may have been received.
TRANSIENT_TRANSPORT = (
    httpx.ConnectError,
    httpx.ReadError,
    httpx.RemoteProtocolError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.PoolTimeout,
)


class HTTPOptions(StrictModel):
    model: str = Field(min_length=1)
    base_url_env: str = Field(min_length=1)
    api_key_env: str = Field(min_length=1)
    timeout_s: PositiveSeconds = 120
    max_tokens: int = Field(default=4096, ge=1)
    temperature: float | None = Field(default=None, ge=0, le=2, allow_inf_nan=False)
    # Newer OpenAI reasoning models reject ``max_tokens`` and require ``max_completion_tokens``.
    token_param: Literal["max_tokens", "max_completion_tokens"] = "max_tokens"
    # Fields set here override the run config's ``retry:`` block for this model.
    retry: RetryPolicy | None = None


class HTTPRunner:
    def __init__(
        self,
        options: dict[str, Any],
        *,
        anthropic: bool = False,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Callable[[float], Awaitable[object]] = asyncio.sleep,
        rng: random.Random | None = None,
        clock: Callable[[], float] = time.monotonic,
        request_timeout: Callable[[float], AbstractAsyncContextManager[object]] = asyncio.timeout,
    ) -> None:
        self.options = HTTPOptions.model_validate(options)
        self.anthropic = anthropic
        self.transport = transport
        # The engine replaces this with the policy resolved from the config and the CLI.
        self.retry_policy = self.options.retry or RetryPolicy()
        self.sleep = sleep
        self.rng = rng or random.Random()
        self.clock = clock
        # Bounds one request by the seconds left; tests replace it to avoid real waiting.
        self.request_timeout = request_timeout

    async def generate(self, task: TaskSpec, workdir: Path) -> Generation:
        opts = self.options
        base_url = os.environ.get(opts.base_url_env)
        key = os.environ.get(opts.api_key_env)
        if not base_url or not key:
            raise RunnerError("required API environment variable is missing")
        headers = (
            {"x-api-key": key, "anthropic-version": "2023-06-01"}
            if self.anthropic
            else {"Authorization": f"Bearer {key}"}
        )
        payload: dict[str, Any] = {
            "model": opts.model,
            "messages": [
                {"role": "user", "content": generation_prompt(task, starter_source(task, workdir))}
            ],
        }
        payload[opts.token_param] = opts.max_tokens
        if opts.temperature is not None:
            payload["temperature"] = opts.temperature
        url = base_url.rstrip("/") + "/" + ("messages" if self.anthropic else "chat/completions")
        # One budget for the whole generation: every request and every wait between them.
        deadline = self.clock() + opts.timeout_s
        try:
            async with httpx.AsyncClient(
                timeout=opts.timeout_s, transport=self.transport, follow_redirects=False
            ) as client:

                async def post() -> httpx.Response:
                    # Never more than timeout_s, since the deadline is timeout_s from the start.
                    remaining = deadline - self.clock()
                    if remaining <= 0:
                        raise TimeoutError("deadline reached")
                    async with self.request_timeout(remaining):
                        response = await client.post(url, headers=headers, json=payload)
                    response.raise_for_status()
                    return response

                response, reasons = await with_retries(
                    post,
                    self.retry_policy,
                    classify=classify_http_error,
                    sleep=self.sleep,
                    rng=self.rng,
                    deadline=deadline,
                    clock=self.clock,
                )
        except RetryError as failure:
            error = _request_error(failure.error, failure.reasons)
            if error is None and failure.reasons:
                # Unexpected, but after retries that the attempt's row must still show.
                error = RunnerError(
                    f"attempt failed: {type(failure.error).__name__}",
                    retry_reasons=failure.reasons,
                )
            if error is None:
                raise failure.error from None
            raise error from failure.error
        except (httpx.HTTPError, ValueError) as exc:
            # Raised outside a request, e.g. while building the client.
            raise RunnerError(f"API request failed: {type(exc).__name__}") from exc
        try:
            return self._complete(task, workdir, response, reasons)
        except RunnerError as exc:
            if exc.retry_reasons or not reasons:
                raise
            raise RunnerError(
                str(exc), timed_out=exc.timed_out, generation=exc.generation, retry_reasons=reasons
            ) from exc
        except Exception as exc:
            if not reasons:
                raise
            # As for the request phase: the retries already made must still reach the row.
            raise RunnerError(
                f"attempt failed: {type(exc).__name__}", retry_reasons=reasons
            ) from exc

    def _complete(
        self, task: TaskSpec, workdir: Path, response: httpx.Response, reasons: list[str]
    ) -> Generation:
        try:
            data = response.json()
            if self.anthropic:
                raw = "\n".join(p["text"] for p in data["content"] if p.get("type") == "text")
                in_key, out_key = "input_tokens", "output_tokens"
            else:
                raw = data["choices"][0]["message"]["content"]
                in_key, out_key = "prompt_tokens", "completion_tokens"
            if not isinstance(raw, str):
                raise ValueError("non-text response")
            usage = data.get("usage") or {}
            # Cost is deliberately not inferred from a pricing table.
            result = Generation(
                raw,
                _tokens(usage.get(in_key)),
                _tokens(usage.get(out_key)),
                _cost(usage.get("cost_usd")),
                tuple(reasons),
            )
        except (KeyError, IndexError, TypeError, ValueError, AttributeError, OverflowError) as exc:
            raise RunnerError("API returned an invalid response", retry_reasons=reasons) from exc
        try:
            code = extract_code(raw)
            (workdir / task.entrypoint).write_text(code, encoding="utf-8")
        except RunnerError as exc:
            raise RunnerError(str(exc), generation=result) from exc
        except OSError as exc:
            raise RunnerError("cannot write generated source", generation=result) from exc
        return result


def classify_http_error(exc: Exception) -> Transient | None:
    """Retry rate limits, overload and dropped connections; reasons never echo the response."""
    if isinstance(exc, httpx.HTTPStatusError):
        response = exc.response
        if response.status_code not in TRANSIENT_STATUS:
            return None
        return Transient(
            f"http_{response.status_code}", parse_retry_after(response.headers.get("retry-after"))
        )
    if isinstance(exc, TRANSIENT_TRANSPORT):
        return Transient(type(exc).__name__)
    # Includes the generation deadline (TimeoutError): a slow model will not get faster.
    return None


def parse_retry_after(value: str | None) -> float | None:
    """Seconds from a ``Retry-After`` header. The HTTP-date form is ignored."""
    if value is None or not re.fullmatch(r"[0-9]+(\.[0-9]+)?", value.strip()):
        return None
    return float(value)


def _request_error(exc: Exception, reasons: list[str]) -> RunnerError | None:
    # Never persist response bodies, URLs, headers, or credential-bearing exceptions.
    if isinstance(exc, (httpx.TimeoutException, TimeoutError)):
        return RunnerError("API request timed out", timed_out=True, retry_reasons=reasons)
    if isinstance(exc, httpx.HTTPStatusError):
        return RunnerError(
            f"API request failed with HTTP {exc.response.status_code}", retry_reasons=reasons
        )
    if isinstance(exc, (httpx.HTTPError, ValueError)):
        return RunnerError(f"API request failed: {type(exc).__name__}", retry_reasons=reasons)
    return None


def _tokens(value: Any) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value < 0:
        raise ValueError("invalid token count")
    return int(value)


def _cost(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("invalid cost")
    try:
        cost = float(value)
    except OverflowError:
        # An integer too large for a float, e.g. 10**400.
        raise ValueError("invalid cost") from None
    if cost < 0 or not math.isfinite(cost):
        raise ValueError("invalid cost")
    return cost
