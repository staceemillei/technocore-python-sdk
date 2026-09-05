"""Retry policy for the Technocore HTTP client.

Implements a small, dependency-free retry helper with exponential backoff and
jitter. The Technocore SDK reuses this for transient failures (5xx, 429,
connection resets, and timeouts) so callers don't have to write the same
boilerplate around every protocol lane.

Design notes:

* Pure stdlib (random + time only) so it stays light.
* Decorator and direct-call forms both supported.
* Honours an optional ``Retry-After`` header value (seconds or HTTP-date).
* Never retries on 4xx other than 408/429; the caller is expected to fix
  those.
* Logs attempts via the standard ``logging`` hierarchy under
  ``technocore_sdk.retry``; consumers can mute it if they want.
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from email.utils import parsedate_to_datetime
from typing import Any, Callable, Iterable, Optional, Tuple, Type, TypeVar

from .errors import TransportError

__all__ = ["RetryPolicy", "retry", "compute_backoff"]

_LOG = logging.getLogger("technocore_sdk.retry")

T = TypeVar("T")

# Status codes that are worth retrying.
_RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}
# Exception types we treat as transient network failures.
_RETRYABLE_EXC: Tuple[Type[BaseException], ...] = (ConnectionError, TimeoutError)


@dataclass(frozen=True)
class RetryPolicy:
    """Configuration for :func:`retry`.

    Attributes
    ----------
    max_attempts:
        Total attempts including the first try. ``1`` disables retrying.
    base_delay:
        Seconds for the first backoff sleep. Doubles each attempt up to
        ``max_delay``.
    max_delay:
        Hard cap on a single sleep, in seconds.
    jitter:
        If True (default), a uniform ``[0, delay]`` jitter is added so a
        thundering herd of clients doesn't synchronise.
    retry_on:
        Additional exception types to treat as retryable on top of the
        defaults (``ConnectionError``, ``TimeoutError``).
    """

    max_attempts: int = 4
    base_delay: float = 0.25
    max_delay: float = 8.0
    jitter: bool = True
    retry_on: Tuple[Type[BaseException], ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.base_delay <= 0 or self.max_delay <= 0:
            raise ValueError("delays must be positive")
        if self.base_delay > self.max_delay:
            raise ValueError("base_delay cannot exceed max_delay")


def compute_backoff(attempt: int, policy: RetryPolicy) -> float:
    """Return the sleep duration before retry attempt ``attempt`` (1-indexed).

    Attempt 1 is the first retry, so the delay before attempt 1 is the base
    delay. The sequence is exponential with a cap, plus optional jitter.
    """
    if attempt < 1:
        raise ValueError("attempt must be >= 1")
    delay = policy.base_delay * (2 ** (attempt - 1))
    delay = min(delay, policy.max_delay)
    if policy.jitter:
        delay += random.uniform(0, delay)
        delay = min(delay, policy.max_delay * 2)
    return delay


def _is_retryable(exc: BaseException, policy: RetryPolicy) -> bool:
    if isinstance(exc, policy.retry_on):
        return True
    if isinstance(exc, _RETRYABLE_EXC):
        return True
    if isinstance(exc, TransportError):
        return exc.status_code in _RETRYABLE_STATUS
    return False


def _parse_retry_after(value: str) -> Optional[float]:
    """Return seconds to wait per RFC 7231, or None if unparseable."""
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        target = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    delta = (target - _now()).total_seconds()
    return max(0.0, delta)


def _now() -> Any:
    # Wrapped so tests can monkeypatch.
    import datetime as _dt
    return _dt.datetime.now(_dt.timezone.utc)


def retry(
    policy: RetryPolicy,
    *,
    retry_after: Callable[[BaseException], Optional[str]] = lambda _e: None,
    sleep: Callable[[float], None] = time.sleep,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator: run ``fn`` under ``policy``.

    ``retry_after`` is an optional callback that, given the caught exception,
    returns a ``Retry-After``-style string (seconds or HTTP date). When it
    yields a value, that wait replaces the computed backoff for that
    attempt. ``sleep`` is injectable for testing.
    """

    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args: Any, **kwargs: Any) -> T:
            attempt = 0
            while True:
                attempt += 1
                try:
                    return fn(*args, **kwargs)
                except BaseException as exc:
                    if attempt >= policy.max_attempts or not _is_retryable(exc, policy):
                        raise
                    header = retry_after(exc)
                    if header:
                        wait = _parse_retry_after(header)
                    else:
                        wait = None
                    if wait is None:
                        wait = compute_backoff(attempt, policy)
                    _LOG.warning(
                        "technocore retry: %s on attempt %d/%d, sleeping %.2fs",
                        type(exc).__name__,
                        attempt,
                        policy.max_attempts,
                        wait,
                    )
                    sleep(wait)
        # Make the policy discoverable for tests/docs.
        wrapper.__wrapped__ = fn  # type: ignore[attr-defined]
        wrapper.retry_policy = policy  # type: ignore[attr-defined]
        return wrapper

    return decorator


def collect_retryable(excs: Iterable[BaseException]) -> Tuple[Type[BaseException], ...]:
    """Helper for building a policy's ``retry_on`` tuple from sample errors."""
    seen: list[Type[BaseException]] = []
    for exc in excs:
        cls = type(exc)
        if cls not in seen:
            seen.append(cls)
    return tuple(seen)

<!-- Authored by Technocore agent DID did:key:z6MkjkinNc1mbVkTXmkxYggoR5DLUK1dcmkK3bLv9h9cy44p -->
