"""Retry utilities for the technocore SDK.

Provides a small, transport-agnostic retry helper that the HTTP client
(and any future transport) can use to wrap idempotent requests.

Design goals:
  * Zero external dependencies beyond the standard library.
  * Explicit, typed policy objects (no hidden globals).
  * Exponential backoff with full jitter, bounded by ``max_backoff``.
  * Honours a caller-provided sleep function so tests can run
    deterministically without monkeypatching ``time.sleep``.

The helper is intentionally minimal. It does not attempt to be a full
resilience library; it exists so the SDK has one consistent answer to
"how do we retry transient errors?" across every protocol lane.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Callable, Iterable, Tuple, Type, TypeVar

from .exceptions import TransientError

T = TypeVar("T")


@dataclass(frozen=True)
class RetryPolicy:
    """Describes how aggressively to retry a transient failure.

    Attributes:
        max_attempts: Total attempts including the first try. Must be >= 1.
        base_backoff: Initial backoff in seconds before the first retry.
        max_backoff: Cap on the computed backoff in seconds.
        jitter: When True, applies full jitter (uniform in [0, backoff]).
        retry_on: Exception types that are considered retryable. Anything
            not listed here propagates immediately.
        sleep: Callable used to wait between attempts. Override in tests.
    """

    max_attempts: int = 3
    base_backoff: float = 0.25
    max_backoff: float = 8.0
    jitter: bool = True
    retry_on: Tuple[Type[BaseException], ...] = (TransientError,)
    sleep: Callable[[float], None] = field(default=time.sleep)

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.base_backoff < 0 or self.max_backoff < 0:
            raise ValueError("backoff values must be non-negative")
        if self.base_backoff > self.max_backoff:
            raise ValueError("base_backoff cannot exceed max_backoff")

    def backoff_for(self, attempt: int) -> float:
        """Return the delay (seconds) before retry number ``attempt``.

        ``attempt`` is 1-indexed: attempt=1 is the first retry, i.e. the
        delay after the initial try failed.
        """
        if attempt < 1:
            raise ValueError("attempt must be >= 1")
        # 2 ** (attempt - 1) gives 1, 2, 4, 8, ... capped at max_backoff.
        raw = min(self.base_backoff * (2 ** (attempt - 1)), self.max_backoff)
        if self.jitter:
            return random.uniform(0.0, raw)
        return raw


def is_retryable(
    exc: BaseException,
    retry_on: Iterable[Type[BaseException]],
) -> bool:
    """Return True if ``exc`` matches any type in ``retry_on``."""
    return isinstance(exc, tuple(retry_on))


def call_with_retry(
    func: Callable[[], T],
    policy: RetryPolicy,
) -> T:
    """Invoke ``func`` under ``policy``, retrying transient failures.

    Raises:
        The last exception encountered if all attempts fail.
        Any non-retryable exception immediately, without retrying.
    """
    if not callable(func):
        raise TypeError("func must be callable")

    attempt = 0
    while True:
        attempt += 1
        try:
            return func()
        except BaseException as exc:
            if not is_retryable(exc, policy.retry_on):
                raise
            if attempt >= policy.max_attempts:
                raise
            delay = policy.backoff_for(attempt)
            policy.sleep(delay)


__all__ = ["RetryPolicy", "call_with_retry", "is_retryable"]

<!-- Authored by Technocore agent DID did:key:z6MkjkinNc1mbVkTXmkxYggoR5DLUK1dcmkK3bLv9h9cy44p -->
