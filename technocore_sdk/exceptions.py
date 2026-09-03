"""Exception hierarchy for the technocore SDK.

Every public method on :class:`technocore_sdk.client.TechnocoreClient` raises
subclasses of :class:`TechnocoreError`. This module centralizes them so
callers can catch a broad ``TechnocoreError`` and drill down by cause, or
catch a specific subclass when they need finer-grained handling (for
instance, retrying on :class:`TransientError` only).

The hierarchy mirrors common HTTP failure modes plus a few SDK-local
conditions:

    TechnocoreError
    +-- TransportError          # connection / DNS / TLS failures
    +-- ProtocolError           # malformed message, bad framing
    +-- AuthenticationError     # DID signature rejected, unknown peer
    +-- RateLimitError          # peer asked us to back off
    +-- NotFoundError           # resource absent on remote
    +-- ServerError             # 5xx-class failures
    +-- TransientError          # safe to retry with backoff
    +-- ConfigurationError      # bad local config, missing key, etc.

Design notes
------------
* All errors carry an optional ``cause`` (the underlying exception, if any)
  and a ``details`` dict for structured context (status code, headers,
  payload excerpt). They stringify to a single line, which keeps log
  pipelines happy.
* Subclasses set sensible defaults for ``retryable`` so retry helpers
  don't need a hand-maintained allow-list.
* Nothing in this module imports anything from ``technocore_sdk.client``
  to avoid a circular dependency.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional


class TechnocoreError(Exception):
    """Base class for every error raised by the technocore SDK.

    Parameters
    ----------
    message:
        Human-readable description. Kept on a single line.
    cause:
        The underlying exception, if this error wraps another.
    details:
        Free-form structured context (status code, peer DID, payload
        excerpt, ...). Kept on the instance as ``self.details``.
    retryable:
        Hint for retry helpers. Defaults to ``False``; subclasses that
        are safe to retry override it.
    """

    retryable: bool = False

    def __init__(
        self,
        message: str,
        *,
        cause: Optional[BaseException] = None,
        details: Optional[Mapping[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.__cause__ = cause  # for `raise ... from ...` semantics
        self.details: dict[str, Any] = dict(details) if details else {}

    def __str__(self) -> str:  # noqa: D401 - keep one-line rendering
        if not self.details:
            return self.message
        # Flatten details into the message so log lines stay single-line.
        parts = ", ".join(f"{k}={v!r}" for k, v in self.details.items())
        return f"{self.message} ({parts})"


class TransportError(TechnocoreError):
    """The HTTP transport itself failed before a response was received.

    Examples: DNS resolution error, TCP reset, TLS handshake failure,
    timeout. Always retryable — the peer never saw the request.
    """

    retryable = True


class ProtocolError(TechnocoreError):
    """The response was received but could not be parsed.

    Raised for malformed JSON, truncated bodies, unknown envelope
    fields, or a signed envelope whose signature did not verify against
    the claimed sender DID. Not retryable — retrying won't make the
    bytes valid.
    """


class AuthenticationError(ProtocolError):
    """The peer rejected our DID signature, or signed with an unknown DID.

    Inherits from :class:`ProtocolError` because the bytes were
    syntactically fine but semantically rejected. Not retryable; the
    caller should refresh credentials or check their DID key.
    """


class RateLimitError(TechnocoreError):
    """The peer asked us to slow down.

    The SDK surfaces ``Retry-After`` (if present) in
    ``self.details['retry_after_seconds']`` so retry helpers can honor
    it without re-parsing headers.
    """

    retryable = True


class NotFoundError(TechnocoreError):
    """The requested resource does not exist on the remote.

    Distinct from a generic 4xx so callers can branch on it cleanly
    (e.g. return ``None`` instead of bubbling an error to the user).
    """


class ServerError(TechnocoreError):
    """A 5xx-class failure from the peer.

    Treated as retryable by default; subclasses or specific status
    codes (501 Not Implemented) may override.
    """

    retryable = True


class TransientError(TechnocoreError):
    """Generic safe-to-retry wrapper.

    Use this when you catch a non-retryable error in a retry loop and
    want to re-raise as something the outer loop knows how to handle
    (for example, mapping a single ``ProtocolError`` on retry #2 into
    a ``TransientError`` so the loop gives up gracefully).
    """

    retryable = True


class ConfigurationError(TechnocoreError):
    """The SDK is misconfigured locally.

    Examples: missing Ed25519 private key, malformed DID document,
    conflicting options on the client constructor. Never retryable —
    the operator must fix the config first.
    """


__all__ = [
    "TechnocoreError",
    "TransportError",
    "ProtocolError",
    "AuthenticationError",
    "RateLimitError",
    "NotFoundError",
    "ServerError",
    "TransientError",
    "ConfigurationError",
]

<!-- Authored by Technocore agent DID did:key:z6MkjkinNc1mbVkTXmkxYggoR5DLUK1dcmkK3bLv9h9cy44p -->
