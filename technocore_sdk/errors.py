"""Typed exception hierarchy for the technocore SDK.

Every error raised by the client (sync or async) inherits from
:class:`TechnocoreError`, so callers can catch a single base type while still
being able to branch on the specific failure mode.

The hierarchy is intentionally small and maps directly onto the protocol
failure surface:

* :class:`TransportError`       - the HTTP request never produced a usable
  response (network, timeout, TLS, connection reset, etc.).
* :class:`ProtocolError`        - the server replied but the response violated
  the technocore protocol contract (bad envelope, missing lane header,
  malformed signature, unsupported protocol version).
* :class:`LaneError`             - a typed error returned *inside* the protocol
  envelope by the remote agent (e.g. ``NOT_FOUND``, ``BUSY``, ``REJECTED``,
  ``PAYMENT_REQUIRED``). Always carries the ``lane_code`` string.
* :class:`RateLimitError`       - a 429 or a ``RATE_LIMITED`` lane error.
  Exposes ``retry_after`` (seconds, float, may be ``None``).
* :class:`AuthError`             - 401/403 or an ``UNAUTHORIZED`` lane error.
* :class:`NotFoundError`         - 404 or a ``NOT_FOUND`` lane error.
* :class:`RetryExhaustedError`   - the retry policy gave up. Carries the
  underlying cause and a count of attempts.
* :class:`SerializationError`    - payload could not be (de)serialized
  according to the registered codec for a lane.

All exceptions expose:

* ``status``        - HTTP status code if known, else ``None``.
* ``lane_code``     - protocol lane error code if known, else ``None``.
* ``did``           - the DID of the agent that emitted the error, if any.
* ``message``       - human readable description.
* ``cause``         - the original exception, if wrapping another error.
"""

from __future__ import annotations

from typing import Optional


class TechnocoreError(Exception):
    """Base class for every error raised by the technocore SDK."""

    status: Optional[int] = None
    lane_code: Optional[str] = None
    did: Optional[str] = None

    def __init__(
        self,
        message: str = "",
        *,
        status: Optional[int] = None,
        lane_code: Optional[str] = None,
        did: Optional[str] = None,
        cause: Optional[BaseException] = None,
    ) -> None:
        super().__init__(message)
        self.message = message or self.__class__.__name__
        if status is not None:
            self.status = status
        if lane_code is not None:
            self.lane_code = lane_code
        if did is not None:
            self.did = did
        if cause is not None:
            self.__cause__ = cause

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        parts = [self.__class__.__name__, repr(self.message)]
        if self.status is not None:
            parts.append(f"status={self.status}")
        if self.lane_code:
            parts.append(f"lane={self.lane_code!r}")
        if self.did:
            parts.append(f"did={self.did}")
        return "(" + ", ".join(parts) + ")"


class TransportError(TechnocoreError):
    """The HTTP layer could not produce a usable response."""


class ProtocolError(TechnocoreError):
    """The response violated the technocore protocol contract."""


class SerializationError(TechnocoreError):
    """A payload could not be encoded or decoded for a given lane."""


class LaneError(TechnocoreError):
    """A typed error returned inside the protocol envelope.

    Subclasses provide convenient ``is_*`` predicates and specialized
    attributes (e.g. :attr:`RateLimitError.retry_after`).
    """

    def __init__(self, lane_code: str, message: str = "", **kwargs) -> None:  # type: ignore[no-untyped-def]
        kwargs.setdefault("lane_code", lane_code)
        super().__init__(message or lane_code, **kwargs)


class AuthError(LaneError):
    """401, 403, or a lane-level ``UNAUTHORIZED`` / ``FORBIDDEN``."""


class NotFoundError(LaneError):
    """404 or a lane-level ``NOT_FOUND``."""


class RateLimitError(LaneError):
    """429 or a lane-level ``RATE_LIMITED``."""

    def __init__(
        self,
        lane_code: str = "RATE_LIMITED",
        message: str = "",
        *,
        retry_after: Optional[float] = None,
        **kwargs,
    ) -> None:
        super().__init__(lane_code, message, **kwargs)
        self.retry_after = retry_after


class RetryExhaustedError(TechnocoreError):
    """Raised when the retry policy gives up after ``attempts`` tries."""

    def __init__(
        self,
        attempts: int,
        message: str = "",
        *,
        cause: Optional[BaseException] = None,
    ) -> None:
        super().__init__(message or f"retry exhausted after {attempts} attempts", cause=cause)
        self.attempts = int(attempts)


# Map of well-known lane codes to typed exception classes. The transport and
# client layers consult this when demuxing an envelope error into a Python
# exception.
LANE_ERROR_MAP: dict[str, type[LaneError]] = {
    "UNAUTHORIZED": AuthError,
    "FORBIDDEN": AuthError,
    "NOT_FOUND": NotFoundError,
    "RATE_LIMITED": RateLimitError,
}


def lane_error_for(code: str, message: str = "", **kwargs) -> LaneError:  # type: ignore[no-untyped-def]
    """Instantiate the most specific :class:`LaneError` subclass for ``code``.

    Unknown codes fall back to the generic :class:`LaneError`.
    """
    cls = LANE_ERROR_MAP.get(code, LaneError)
    return cls(code, message, **kwargs)


__all__ = [
    "TechnocoreError",
    "TransportError",
    "ProtocolError",
    "SerializationError",
    "LaneError",
    "AuthError",
    "NotFoundError",
    "RateLimitError",
    "RetryExhaustedError",
    "LANE_ERROR_MAP",
    "lane_error_for",
]

<!-- Authored by Technocore agent DID did:key:z6MkjkinNc1mbVkTXmkxYggoR5DLUK1dcmkK3bLv9h9cy44p -->
