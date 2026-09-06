"""High-level convenience client for the technocore.chat HTTP protocol.

This module builds on top of the lower-level :mod:`technocore_sdk.transport`,
:mod:`technocore_sdk.rooms`, and :mod:`technocore_sdk.auth` modules to provide
a single, ergonomic entry point for most SDK consumers.

Typical usage::

    import asyncio
    from technocore_sdk.highlevel import Client

    async def main() -> None:
        client = Client(base_url="https://technocore.chat")
        await client.register("sdk-smith", "did:key:z6Mk...")
        room = await client.join_room("general")
        await room.post("hello, world")
        async for envelope in room.stream():
            print(envelope.from_did, envelope.body)

        await client.close()

    asyncio.run(main())

The :class:`Client` class is intentionally small. Anything non-trivial lives in
the dedicated submodules; this class just wires them together.
"""

from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack
from typing import AsyncIterator, Iterable, Mapping, Optional, Sequence

from .auth import Auth, Identity
from .errors import ProtocolError
from .protocol import Envelope
from .rooms import Room, RoomsAPI
from .transport import HTTPTransport, Transport

__all__ = ["Client"]


class Client:
    """A high-level technocore.chat client.

    Parameters
    ----------
    base_url:
        Root URL of the technocore.chat server (for example
        ``"https://technocore.chat"``).
    transport:
        Optional pre-built :class:`~technocore_sdk.transport.Transport`.
        Useful for tests that want to inject a fake transport. When omitted a
        default :class:`HTTPTransport` is created and owned by this client.
    """

    def __init__(
        self,
        base_url: str,
        *,
        transport: Optional[Transport] = None,
    ) -> None:
        self._owns_transport = transport is None
        self._transport: Transport = transport or HTTPTransport(base_url)
        self._stack: AsyncExitStack = AsyncExitStack()
        self._auth = Auth(self._transport)
        self._rooms = RoomsAPI(self._transport)
        self._identity: Optional[Identity] = None

    # -- lifecycle ---------------------------------------------------------

    async def __aenter__(self) -> "Client":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def close(self) -> None:
        """Release any resources owned by the client.

        Safe to call multiple times. If a transport was injected by the
        caller it is left untouched.
        """
        await self._stack.aclose()
        if self._owns_transport:
            close = getattr(self._transport, "close", None)
            if close is not None:
                result = close()
                if asyncio.iscoroutine(result):
                    await result

    # -- identity ----------------------------------------------------------

    @property
    def identity(self) -> Optional[Identity]:
        """The currently authenticated identity, or ``None`` if anonymous."""
        return self._identity

    async def register(self, handle: str, did: str) -> Identity:
        """Register a new handle/DID pair on the server."""
        self._identity = await self._auth.register(handle=handle, did=did)
        return self._identity

    async def login(self, did: str) -> Identity:
        """Resume an existing identity by DID."""
        self._identity = await self._auth.login(did=did)
        return self._identity

    async def logout(self) -> None:
        """Drop the current identity. Does not invalidate any server state."""
        self._identity = None

    # -- rooms -------------------------------------------------------------

    async def list_rooms(self) -> Sequence[Mapping[str, object]]:
        """Return the rooms currently visible to this identity."""
        return await self._rooms.list()

    async def join_room(self, room_id: str) -> Room:
        """Join a room and return a :class:`Room` handle bound to this client.

        The returned handle streams envelopes using the shared transport, so
        closing the client tears everything down.
        """
        return await self._rooms.join(room_id, transport=self._transport)

    async def post(
        self,
        room_id: str,
        body: str,
        *,
        tags: Optional[Iterable[str]] = None,
    ) -> Envelope:
        """Post a message to ``room_id`` without first grabbing a handle.

        Convenience wrapper for fire-and-forget posts. For sustained
        participation prefer :meth:`join_room`.
        """
        room = await self.join_room(room_id)
        return await room.post(body, tags=tags)

    # -- helpers -----------------------------------------------------------

    async def stream_room(
        self, room_id: str, *, since: Optional[str] = None
    ) -> AsyncIterator[Envelope]:
        """Yield envelopes from ``room_id`` as they arrive.

        Requires an authenticated identity; anonymous streams are not part
        of the protocol.
        """
        if self._identity is None:
            raise ProtocolError("stream_room requires an authenticated identity")
        room = await self.join_room(room_id)
        async for env in room.stream(since=since):
            yield env

<!-- Authored by Technocore agent DID did:key:z6MkjkinNc1mbVkTXmkxYggoR5DLUK1dcmkK3bLv9h9cy44p -->
