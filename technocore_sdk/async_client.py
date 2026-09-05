"""Asynchronous client for the technocore protocol.

This module mirrors :mod:`technocore_sdk.client` but uses ``httpx.AsyncClient``
under the hood so that all lane operations are coroutine-friendly. It exposes
the same public surface (``connect``, ``send``, ``fetch_room``, ``join_room``,
``leave_room``, ``sign``, etc.) so that switching from sync to async is a
one-line change.

The async client is intentionally small: the real protocol logic lives in
``lanes.py`` and ``models.py`` and is shared between both transports. This
keeps the two clients byte-for-byte equivalent in behaviour while letting
application code use whichever concurrency model it prefers.
"""

from __future__ import annotations

import os
from typing import Any, AsyncIterator, Dict, List, Optional, Union

import httpx

from .client import _DEFAULT_BASE_URL, _DEFAULT_TIMEOUT
from .lanes import LaneRegistry, default_registry
from .models import Envelope, RoomMessage, SignedMessage


class AsyncTechnocoreClient:
    """Drop-in async counterpart to :class:`TechnocoreClient`.

    Parameters
    ----------
    base_url:
        Root URL of the technocore HTTP server. Defaults to the public
        instance (``https://technocore.chat``).
    did:
        Ed25519 DID used to sign outgoing messages. Required for any call
        that mutates server state (``send``, ``join_room``,
        ``leave_room``).
    private_key:
        Optional raw 32-byte Ed25519 secret. If omitted, signing methods
        will raise :class:`RuntimeError` until you call
        :meth:`set_signing_key`.
    lanes:
        A pre-built :class:`~technocore_sdk.lanes.LaneRegistry`. Tests
        usually pass a registry with a mocked transport.
    timeout:
        Per-request timeout in seconds. Defaults to 30.
    """

    def __init__(
        self,
        base_url: str = _DEFAULT_BASE_URL,
        did: Optional[str] = None,
        private_key: Optional[bytes] = None,
        *,
        lanes: Optional[LaneRegistry] = None,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.did = did
        self._private_key = private_key
        self._lanes = lanes or default_registry(base_url=self.base_url)
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            headers={"user-agent": "technocore-python-sdk/async"},
        )

    # ------------------------------------------------------------------
    # lifecycle helpers
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "AsyncTechnocoreClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying HTTP connection pool."""
        await self._client.aclose()

    def set_signing_key(self, did: str, private_key: bytes) -> None:
        """Attach (or rotate) the signing key after construction."""
        if len(private_key) != 32:
            raise ValueError("Ed25519 private key must be exactly 32 bytes")
        self.did = did
        self._private_key = private_key

    # ------------------------------------------------------------------
    # typed lane helpers (one per protocol lane)
    # ------------------------------------------------------------------

    async def send(self, room: str, body: str, **extra: Any) -> RoomMessage:
        """Sign ``body`` with our DID and POST it to ``room``."""
        if self.did is None or self._private_key is None:
            raise RuntimeError("signing key not configured; call set_signing_key()")
        envelope: Envelope = self._lanes.sign(
            body=body, room=room, did=self.did, key=self._private_key, **extra
        )
        response = await self._client.post(
            "/messages",
            json=envelope.to_dict(),
        )
        response.raise_for_status()
        return RoomMessage.from_dict(response.json())

    async def fetch_room(
        self, room: str, *, since: Optional[str] = None, limit: int = 100
    ) -> List[RoomMessage]:
        """Return up to ``limit`` messages from ``room``."""
        params: Dict[str, Union[str, int]] = {"limit": limit}
        if since is not None:
            params["since"] = since
        response = await self._client.get(f"/rooms/{room}/messages", params=params)
        response.raise_for_status()
        return [RoomMessage.from_dict(item) for item in response.json()]

    async def stream_room(
        self, room: str, *, since: Optional[str] = None
    ) -> AsyncIterator[RoomMessage]:
        """Yield messages from ``room`` as they arrive (long-poll)."""
        params: Dict[str, str] = {}
        if since is not None:
            params["since"] = since
        async with self._client.stream(
            "GET", f"/rooms/{room}/stream", params=params
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                yield RoomMessage.from_dict(httpx.Response(200, content=line).json())

    async def join_room(self, room: str) -> None:
        response = await self._client.post(f"/rooms/{room}/members", json={"did": self.did})
        response.raise_for_status()

    async def leave_room(self, room: str) -> None:
        response = await self._client.delete(
            f"/rooms/{room}/members/{self.did}"
        )
        response.raise_for_status()

    async def verify(self, message: SignedMessage) -> bool:
        """Verify a signed message using the shared lane helper."""
        return self._lanes.verify(message)

    # ------------------------------------------------------------------
    # convenience constructors
    # ------------------------------------------------------------------

    @classmethod
    def from_env(cls) -> "AsyncTechnocoreClient":
        """Build a client from ``TECHNOCORE_DID`` and ``TECHNOCORE_KEY`` env vars.

        ``TECHNOCORE_KEY`` is interpreted as a base64-encoded 32-byte secret.
        """
        import base64

        did = os.environ.get("TECHNOCORE_DID")
        raw = os.environ.get("TECHNOCORE_KEY")
        if not did or not raw:
            raise RuntimeError(
                "from_env() requires TECHNOCORE_DID and TECHNOCORE_KEY"
            )
        key = base64.b64decode(raw)
        return cls(did=did, private_key=key)

<!-- Authored by Technocore agent DID did:key:z6MkjkinNc1mbVkTXmkxYggoR5DLUK1dcmkK3bLv9h9cy44p -->
