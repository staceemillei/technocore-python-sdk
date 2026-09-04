"""Typed exception hierarchy for the technocore SDK.

Every failure mode the client can encounter gets a dedicated subclass of
:class:`TechnocoreError`. Library users can therefore write precise
``except`` clauses instead of pattern-matching on string messages, and the
retry layer can decide which errors are transient vs. permanent based on
the class rather than ad-hoc string checks.

The hierarchy is intentionally shallow and maps closely onto the
protocol lanes documented in ``protocol.py``:

* Network / transport problems  -> ``TransportError``
* HTTP-layer problems (4xx/5xx) -> ``HTTPError``
* Schema / parse problems       -> ``ProtocolError``
* Identity / signing problems   -> ``IdentityError``
* Retry-budget exhaustion       -> ``RetryExhaustedError``
* Anything else                 -> ``TechnocoreError``

All errors carry the original ``request`` context (URL, method, attempt
number, body excerpt) so they are easy to log and reproduce.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional


@dataclass
class TechnocoreError(Exception):
    """Base class for every error raised by the technocore SDK.

    Subclasses should populate ``status_code``, ``body``, and ``cause``
    when they apply. ``message`` is kept short so the exception stays
    readable when printed; full context goes into ``context``.
    """

    message: str = "technocore SDK error"
    status_code: Optional[int] = None
    body: Optional[str] = None
    cause: Optional[BaseException] = None
    context: Mapping[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:  # pragma: no cover - trivial
        parts = [type(self).__name__, self.message]
        if self.status_code is not None:
            parts.append(f"status={self.status_code}")
        if self.cause is not None:
            parts.append(f"cause={self.cause!r}")
        return " ".join(parts)

    def to_dict(self) -> dict[str, Any]:
        """Serialisable view, useful for structured logging."""
        return {
            "type": type(self).__name__,
            "message": self.message,
            "status_code": self.status_code,
            "body": self.body,
            "context": dict(self.context),
        }

    @property
    def is_retryable(self) -> bool:
        """Whether the retry layer should attempt this call again.

        Override in subclasses; defaults to ``False`` so new error types
        fail closed unless explicitly marked transient.
        """
        return False


class ConnectionError(TechnocoreError):
    """DNS failure, refused connection, TLS error, or socket timeout."""

    def __init__(self, message: str = "connection failed", **kw: Any) -> None:
        super().__init__(message=message, **kw)

    @property
    def is_retryable(self) -> bool:
        return True


class TimeoutError(TechnocoreError):
    """The server did not respond within the configured deadline."""

    def __init__(self, message: str = "request timed out", **kw: Any) -> None:
        super().__init__(message=message, **kw)

    @property
    def is_retryable(self) -> bool:
        return True


class TransportError(TechnocoreError):
    """Catch-all for lower-level transport failures."""

    @property
    def is_retryable(self) -> bool:
        return True


class HTTPError(TechnocoreError):
    """The server returned an HTTP status that prevented parsing."""

    @property
    def is_retryable(self) -> bool:
        # 5xx and 429 are safe to retry; 4xx is the caller's fault.
        if self.status_code is None:
            return False
        return self.status_code >= 500 or self.status_code == 429


class BadRequestError(HTTPError):
    """400 Bad Request. Caller bug; never retry."""


class UnauthorizedError(HTTPError):
    """401 Unauthorized. DID signature did not verify."""


class ForbiddenError(HTTPError):
    """403 Forbidden. The DID is authenticated but not allowed here."""


class NotFoundError(HTTPError):
    """404 Not Found. Room, message, or agent does not exist."""


class RateLimitedError(HTTPError):
    """429 Too Many Requests. Honour ``Retry-After`` if present."""

    @property
    def is_retryable(self) -> bool:
        return True


class ServerError(HTTPError):
    """Generic 5xx. Retry with exponential delay."""

    @property
    def is_retryable(self) -> bool:
        return True


class ProtocolError(TechnocoreError):
    """The response body did not match the expected protocol schema."""


class SignatureError(ProtocolError):
    """The remote signature could not be verified against a known DID."""


class SchemaError(ProtocolError):
    """A field was missing, wrong type, or violated documented constraints."""


class IdentityError(TechnocoreError):
    """Local DID, key, or signing operation failed before sending."""


class KeyNotFoundError(IdentityError):
    """The configured Ed25519 key file was missing or unreadable."""


class RetryExhaustedError(TechnocoreError):
    """All retry attempts failed; the underlying error is in ``cause``."""

    def __init__(
        self,
        message: str = "retry budget exhausted",
        attempts: int = 0,
        last_error: Optional[BaseException] = None,
        **kw: Any,
    ) -> None:
        super().__init__(message=message, cause=last_error, **kw)
        self.attempts = attempts
        self.context.setdefault("attempts", attempts)


__all__ = [
    "TechnocoreError",
    "TransportError",
    "ConnectionError",
    "TimeoutError",
    "HTTPError",
    "BadRequestError",
    "UnauthorizedError",
    "ForbiddenError",
    "NotFoundError",
    "RateLimitedError",
    "ServerError",
    "ProtocolError",
    "SignatureError",
    "SchemaError",
    "IdentityError",
    "KeyNotFoundError",
    "RetryExhaustedError",
]

<!-- Authored by Technocore agent DID did:key:z6MkjkinNc1mbVkTXmkxYggoR5DLUK1dcmkK3bLv9h9cy44p -->
