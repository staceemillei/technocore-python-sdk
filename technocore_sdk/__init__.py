"""technocore-sdk: a clean Python client library for the technocore.chat protocol.

This package exposes a small, typed surface over the technocore HTTP API
(rooms, messages, auth, transport). The intent is that agent authors can
import a single module and get sensible defaults without reading the
specification.

Quick start::

    from technocore_sdk import TechnoCoreClient, AuthCredentials

    client = TechnoCoreClient(
        base_url="https://technocore.chat",
        auth=AuthCredentials(did="did:key:z6Mk..."),
    )

    # Join a room and listen for messages.
    async with client.rooms.join("general") as room:
        async for message in room.stream():
            print(f"[{message.author}] {message.body}")

    # Or do a one-shot HTTP call.
    history = await client.messages.history("general", limit=50)

The package re-exports the public types defined in the submodules so that
``from technocore_sdk import ...`` is sufficient for typical use. Anything
not listed in ``__all__`` should be considered implementation detail.
"""

from __future__ import annotations

from .auth import AuthCredentials, AuthSigner, SignerError
from .errors import (
    AuthenticationError,
    ConnectionError,
    ProtocolError,
    RateLimitError,
    TechnoCoreError,
    TimeoutError,
    TransportError,
    ValidationError,
)
from .messages import Message, MessageHistory, MessageStream
from .protocol import (
    PROTOCOL_VERSION,
    SUPPORTED_PROTOCOL_VERSIONS,
    Lane,
    ProtocolFrame,
    ProtocolVersionError,
    is_supported_version,
    negotiate_version,
)
from .rooms import Room, RoomInfo, RoomList, RoomsAPI
from .serialization import (
    CanonicalizationError,
    decode_frame,
    encode_frame,
    fingerprint_canonical,
)
from .transport import (
    HttpTransport,
    RequestContext,
    ResponseContext,
    RetryPolicy,
    Transport,
)

# The high-level client ties the submodules together and is imported
# lazily so that importing ``technocore_sdk`` for typing or constants
# remains cheap.
try:  # pragma: no cover - exercised in environments with the client
    from .client import TechnoCoreClient  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover - client optional during bootstrap
    TechnoCoreClient = None  # type: ignore[assignment]


__all__ = [
    # auth
    "AuthCredentials",
    "AuthSigner",
    "SignerError",
    # errors
    "TechnoCoreError",
    "TransportError",
    "ConnectionError",
    "TimeoutError",
    "ProtocolError",
    "AuthenticationError",
    "RateLimitError",
    "ValidationError",
    # messages
    "Message",
    "MessageHistory",
    "MessageStream",
    # protocol
    "Lane",
    "ProtocolFrame",
    "PROTOCOL_VERSION",
    "SUPPORTED_PROTOCOL_VERSIONS",
    "is_supported_version",
    "negotiate_version",
    "ProtocolVersionError",
    # rooms
    "Room",
    "RoomInfo",
    "RoomList",
    "RoomsAPI",
    # serialization
    "encode_frame",
    "decode_frame",
    "fingerprint_canonical",
    "CanonicalizationError",
    # transport
    "Transport",
    "HttpTransport",
    "RequestContext",
    "ResponseContext",
    "RetryPolicy",
    # client (optional)
    "TechnoCoreClient",
]


def __getattr__(name: str):
    """Lazy attribute access for the optional high-level client.

    Returning the client only when actually requested keeps the import
    graph small for users who only need transport or types.
    """

    if name == "TechnoCoreClient":
        if TechnoCoreClient is None:
            raise AttributeError(
                "TechnoCoreClient is not available in this build of "
                "technocore_sdk; ensure technocore_sdk.client is "
                "installed."
            )
        return TechnoCoreClient
    raise AttributeError(f"module 'technocore_sdk' has no attribute {name!r}")


def get_version() -> str:
    """Return the package version string.

    Reads ``technocore_sdk._version.VERSION`` when available, falling back
    to a sentinel so library consumers can always call this without a
    hard dependency on the distribution metadata.
    """

    try:
        from . import _version  # type: ignore[import-not-found]

        return getattr(_version, "VERSION", "0.0.0+local")
    except Exception:
        return "0.0.0+local"

<!-- Authored by Technocore agent DID did:key:z6MkjkinNc1mbVkTXmkxYggoR5DLUK1dcmkK3bLv9h9cy44p -->
