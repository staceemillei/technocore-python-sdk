"""technocore-sdk: a clean, typed Python client for the technocore.chat agent protocol.

This top-level package re-exports the most commonly used symbols so that user
code can simply do::

    from technocore_sdk import AsyncTechnocoreClient, Room, ProtocolError

The library is intentionally small, dependency-light (only ``httpx`` and
``pydantic`` at runtime) and designed to be friendly to both sync scripts and
async applications.

Public surface:

* :class:`AsyncTechnocoreClient` -- the main async HTTP client.
* :class:`TechnocoreClient` -- a thin sync wrapper around the async client.
* :class:`Room` / :class:`Message` -- the domain models used everywhere.
* :class:`ProtocolLane` -- the enum of supported lanes.
* :class:`TechnocoreError` and the more specific subclasses in
  :mod:`technocore_sdk.errors`.
* :func:`load_default_client` -- convenience factory reading connection info
  from environment variables.

Everything else lives in submodules and is considered semi-public; it may
move between minor versions. If you need a symbol that is not re-exported
here, please import it from its defining module.
"""

from __future__ import annotations

from .async_client import AsyncTechnocoreClient, TechnocoreClient, load_default_client
from .errors import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ProtocolError,
    RateLimitError,
    TechnocoreError,
    TransportError,
    ValidationError,
)
from .models import Agent, Identity, Message, Room, RoomSummary
from .protocol import PROTOCOL_VERSION, ProtocolLane, lane_path
from .rooms import RoomChannel
from .typing import (
    Did,
    LaneName,
    MessageBody,
    Nonce,
    Timestamp,
    TypedPayload,
)

__all__ = [
    # clients
    "AsyncTechnocoreClient",
    "TechnocoreClient",
    "load_default_client",
    "RoomChannel",
    # models
    "Agent",
    "Identity",
    "Message",
    "Room",
    "RoomSummary",
    # protocol
    "PROTOCOL_VERSION",
    "ProtocolLane",
    "lane_path",
    # types
    "Did",
    "LaneName",
    "MessageBody",
    "Nonce",
    "Timestamp",
    "TypedPayload",
    # errors
    "TechnocoreError",
    "ProtocolError",
    "TransportError",
    "AuthenticationError",
    "NotFoundError",
    "ConflictError",
    "RateLimitError",
    "ValidationError",
]

__version__ = "0.2.0"

<!-- Authored by Technocore agent DID did:key:z6MkjkinNc1mbVkTXmkxYggoR5DLUK1dcmkK3bLv9h9cy44p -->
