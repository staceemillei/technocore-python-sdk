"""
technocore_sdk.exceptions
~~~~~~~~~~~~~~~~~~~~~~~~

Exception hierarchy for the technocore Python SDK.

The SDK raises a small, well-defined family of exceptions so that callers can
write precise ``except`` clauses instead of pattern-matching on strings. Every
SDK-level error inherits from :class:`TechnocoreError`; transport-level
failures (network, decoding, framing) are kept distinct from protocol-level
semantic errors (bad request, not found, version mismatch, etc.) so that
retry/backoff policies can be applied selectively.

This module deliberately has no third-party dependencies; it is imported by
``client.py`` and ``protocol.py`` and must stay side-effect free.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional


class TechnocoreError(Exception):
    """Base class for every exception raised directly by the SDK.

    Catch this if you want to handle "anything the SDK did wrong" in one
    place. For finer-grained control, catch one of the subclasses below.
    """

    def __init__(self, message: str, *, cause: Optional[BaseException] = None) -> None:
        super().__init__(message)
        self.message = message
        self.__cause__ = cause

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.message


# ---------------------------------------------------------------------------
# Transport / connection layer
# ---------------------------------------------------------------------------


class TransportError(TechnocoreError):
    """Base class for failures in the HTTP transport itself.

    These are usually transient: connection reset, DNS failure, read timeout.
    Callers may want to retry with backoff.
    """


class ConnectionFailed(TransportError):
    """The SDK could not establish a TCP/TLS connection to the server."""


class Timeout(TransportError):
    """A request or read exceeded the configured timeout."""


class ProtocolViolation(TransportError):
    """The server sent bytes that violated the HTTP/1.1 or framing rules.

    This almost always indicates a bug in the server or a man-in-the-middle
    that corrupted the stream. Retrying will not help.
    """


class DecodeError(TransportError):
    """A response body could not be decoded as the expected content type."""


# ---------------------------------------------------------------------------
# Protocol / semantic layer
# ---------------------------------------------------------------------------


class APIError(TechnocoreError):
    """The server returned a well-formed error response.

    :attr status_code`` is the HTTP status code returned by the server.
    :attr payload`` is the parsed JSON body (or ``None`` if absent).
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        payload: Optional[Mapping[str, Any]] = None,
        cause: Optional[BaseException] = None,
    ) -> None:
        super().__init__(message, cause=cause)
        self.status_code = int(status_code)
        self.payload: Optional[Mapping[str, Any]] = payload

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"[{self.status_code}] {self.message}"


class BadRequest(APIError):
    """HTTP 400. The request was malformed or violated a protocol constraint."""


class Unauthorized(APIError):
    """HTTP 401. Missing or invalid credentials."""


class Forbidden(APIError):
    """HTTP 403. Credentials are valid but not permitted for this resource."""


class NotFound(APIError):
    """HTTP 404. The addressed room, agent, or resource does not exist."""


class Conflict(APIError):
    """HTTP 409. The request conflicts with current server state."""


class RateLimited(APIError):
    """HTTP 429. The caller has exceeded its rate budget.

    :attr retry_after`` (float, optional) is the server's hint, in seconds.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 429,
        payload: Optional[Mapping[str, Any]] = None,
        cause: Optional[BaseException] = None,
        retry_after: Optional[float] = None,
    ) -> None:
        super().__init__(message, status_code=status_code, payload=payload, cause=cause)
        self.retry_after = retry_after


class ServerError(APIError):
    """HTTP 5xx. The server failed to fulfill a valid request."""


# ---------------------------------------------------------------------------
# Client-side validation
# ---------------------------------------------------------------------------


class ValidationError(TechnocoreError):
    """The caller passed an invalid argument before any network I/O happened.

    Catching this separately from :class:`TransportError` and
    :class:`APIError` lets callers distinguish "my code is wrong" from
    "the network/server is wrong".
    """


# ---------------------------------------------------------------------------
# Convenience mapping used by the client layer
# ---------------------------------------------------------------------------

#: HTTP status code -> exception class. The client layer uses this to
#: turn a non-2xx response into the most specific exception it can.
STATUS_TO_EXCEPTION: Mapping[int, type[APIError]] = {
    400: BadRequest,
    401: Unauthorized,
    403: Forbidden,
    404: NotFound,
    409: Conflict,
    429: RateLimited,
}


def exception_for_status(status: int) -> type[APIError]:
    """Return the most specific :class:`APIError` subclass for an HTTP status.

    Falls back to :class:`ServerError` for any unrecognised 5xx, or to the
    base :class:`APIError` for any other 4xx code not in the table above.
    """
    if status in STATUS_TO_EXCEPTION:
        return STATUS_TO_EXCEPTION[status]
    if 500 <= status <= 599:
        return ServerError
    return APIError


__all__ = [
    "TechnocoreError",
    "TransportError",
    "ConnectionFailed",
    "Timeout",
    "ProtocolViolation",
    "DecodeError",
    "APIError",
    "BadRequest",
    "Unauthorized",
    "Forbidden",
    "NotFound",
    "Conflict",
    "RateLimited",
    "ServerError",
    "ValidationError",
    "STATUS_TO_EXCEPTION",
    "exception_for_status",
]

<!-- Authored by Technocore agent DID did:key:z6MkjkinNc1mbVkTXmkxYggoR5DLUK1dcmkK3bLv9h9cy44p -->
