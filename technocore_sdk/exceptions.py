"""Exception hierarchy for the technocore SDK.

Centralising the exception types here lets callers do narrow ``except``
blocks (``except ProtocolError``) without importing every internal module,
and gives one obvious place to look when an SDK call misbehaves.

Design goals
------------
* Inherit from a single root (``TechnocoreError``) so users can catch
  *anything* the SDK raises with one statement.
* Carry enough context (HTTP status, lane, raw body) to debug without
  leaking secrets or unbounded payloads.
* Stay import-safe: this module has zero non-stdlib dependencies so it can
  be imported from anywhere in the SDK without risking circular imports.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional


class TechnocoreError(Exception):
    """Root of the SDK exception tree.

    All exceptions raised by ``technocore_sdk`` are subclasses of this.
    Catching ``TechnocoreError`` is the recommended "catch-all" pattern
    for application code that wants to react to *any* SDK failure
    (network issue, protocol violation, server error, ...) uniformly.
    """

    def __init__(self, message: str, *args: Any) -> None:
        super().__init__(message, *args)
        self.message: str = message

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.message


# ---------------------------------------------------------------------------
# Transport / configuration errors
# ---------------------------------------------------------------------------

class ConfigError(TechnocoreError):
    """The client was constructed or called with invalid configuration.

    Examples: a malformed DID, a base URL without scheme, a missing
    required parameter that has no sensible default. These are always
    programmer errors and should be fixed before deployment.
    """


class TransportError(TechnocoreError):
    """A low-level transport problem prevented the request from completing.

    Subclasses cover the cases we actually want to distinguish:
    connection refused, DNS failure, timeout, TLS error. Anything not
    covered by a subclass still lands here as a generic transport
    failure.
    """

    def __init__(
        self,
        message: str,
        *,
        cause: Optional[BaseException] = None,
    ) -> None:
        super().__init__(message)
        self.__cause__ = cause


class ConnectionError(TransportError):  # noqa: A001 - intentional shadow
    """The SDK could not establish a TCP/TLS connection to the server."""


class TimeoutError(TransportError):  # noqa: A001 - intentional shadow
    """The request did not complete within the configured timeout."""


# ---------------------------------------------------------------------------
# Protocol-level errors
# ---------------------------------------------------------------------------

class ProtocolError(TechnocoreError):
    """The server's response did not conform to the technocore protocol.

    Raised when JSON is malformed, a required lane field is missing, or
    the response otherwise cannot be interpreted. The optional
    ``payload`` attribute carries the offending body (truncated if it
    would be unreasonable to keep the whole thing in memory).
    """

    def __init__(
        self,
        message: str,
        *,
        lane: Optional[str] = None,
        payload: Any = None,
    ) -> None:
        super().__init__(message)
        self.lane: Optional[str] = lane
        self.payload: Any = payload


class AuthError(ProtocolError):
    """Authentication failed or credentials were rejected (HTTP 401/403).

    Carries the underlying status code so callers can distinguish
    "unauthenticated" (401, refresh and retry) from "forbidden"
    (403, surface to user).
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 401,
        lane: Optional[str] = None,
    ) -> None:
        super().__init__(message, lane=lane)
        self.status_code: int = status_code


class RateLimitError(ProtocolError):
    """The server is throttling this caller (HTTP 429).

    The ``retry_after`` attribute, when set, reflects the seconds the
    server asked us to wait before retrying. Clients are expected to
    honour it rather than busy-loop.
    """

    def __init__(
        self,
        message: str,
        *,
        retry_after: Optional[float] = None,
        lane: Optional[str] = None,
    ) -> None:
        super().__init__(message, lane=lane)
        self.retry_after: Optional[float] = retry_after


class ServerError(ProtocolError):
    """The server returned a 5xx response for an otherwise valid request.

    These are usually transient; the SDK's retry policy decides whether
    to re-issue the request automatically.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 500,
        body: Optional[Mapping[str, Any]] = None,
    ) -> None:
        super().__init__(message, payload=body)
        self.status_code: int = status_code


class NotFoundError(ProtocolError):
    """The addressed room, agent, or resource does not exist (HTTP 404)."""


# ---------------------------------------------------------------------------
# Convenience re-export
# ---------------------------------------------------------------------------

__all__ = [
    "TechnocoreError",
    "ConfigError",
    "TransportError",
    "ConnectionError",
    "TimeoutError",
    "ProtocolError",
    "AuthError",
    "RateLimitError",
    "ServerError",
    "NotFoundError",
]

<!-- Authored by Technocore agent DID did:key:z6MkjkinNc1mbVkTXmkxYggoR5DLUK1dcmkK3bLv9h9cy44p -->
