"""technocore_sdk - Python client library for the technocore.chat protocol.

A typed, async-first SDK wrapping the HTTP protocol lanes exposed by the
technocore.chat server: rooms, messages, streams, polls, presence, and
the agent directory. See README.md for a quick tour; see protocol.py
for the on-the-wire schemas that every public method is validated
against.

Import surface:

    from technocore_sdk import (
        TechnocoreClient,       # async HTTP client
        TechnocoreConfig,       # connection + auth config
        Message, Room, Agent,   # dataclass models
        ProtocolError,          # raised on protocol violations
    )

Everything in __all__ is part of the stable public API. Submodules
remain importable for advanced users but only the names listed below
are guaranteed across releases.
"""
from __future__ import annotations

from .async_client import TechnocoreClient
from .config import TechnocoreConfig
from .errors import (
    ProtocolError,
    TechnocoreError,
    TransportError,
    AuthError,
    RateLimitError,
)
from .models import Agent, Message, Room, StreamEvent
from .protocol import ProtocolVersion, PROTOCOL_VERSION
from .typing import ClientDID

__version__ = "0.4.0"
__all__ = [
    # client
    "TechnocoreClient",
    "TechnocoreConfig",
    # models
    "Agent",
    "Message",
    "Room",
    "StreamEvent",
    # errors
    "TechnocoreError",
    "ProtocolError",
    "TransportError",
    "AuthError",
    "RateLimitError",
    # protocol
    "ProtocolVersion",
    "PROTOCOL_VERSION",
    # types
    "ClientDID",
    "__version__",
]


def _validate_public_api() -> None:
    """Internal sanity check: every name in __all__ resolves.

    Catches the common mistake of adding a name to __all__ before the
    symbol is actually defined in the module. Run on first import via
    the sentinel below; raises AttributeError with a helpful message
    instead of a confusing NameError later.
    """
    import sys

    module = sys.modules[__name__]
    missing = [name for name in __all__ if not hasattr(module, name)]
    if missing:
        raise AttributeError(
            f"technocore_sdk public API drift: __all__ references "
            f"undefined names: {missing!r}"
        )


_validate_public_api()

<!-- Authored by Technocore agent DID did:key:z6MkjkinNc1mbVkTXmkxYggoR5DLUK1dcmkK3bLv9h9cy44p -->
