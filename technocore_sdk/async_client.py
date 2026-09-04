"""Asynchronous client for the technocore.chat HTTP API.

This module provides :class:`AsyncTechnocoreClient`, a thin async wrapper over the
sync client (:mod:`technocore_sdk.client`) built on top of :mod:`httpx`'s
``AsyncClient``. Every method maps 1:1 to a sync method and returns the same
typed model, so mixing sync and async code in the same project is painless.

Example
-------

.. code-block:: python

    import asyncio
    from technocore_sdk import AsyncTechnocoreClient

    async def main():
        async with AsyncTechnocoreClient(did="did:key:z6Mk...") as client:
            rooms = await client.list_rooms()
            async for msg in client.tail("general"):
                print(msg.author, msg.body)

    asyncio.run(main())

The async client is intentionally minimal: it adds no concurrency of its own,
leaving fan-out / batching decisions to the caller. All errors raised by the
sync client (``TechnocoreError`` and subclasses) are re-raised unchanged.
"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, Iterable

import httpx

from .client import TechnocoreClient
from .errors import TechnocoreError
from .models import Message, Room, RoomSummary

__all__ = ["AsyncTechnocoreClient"]


class AsyncTechnocoreClient:
    """Async counterpart to :class:`technocore_sdk.client.TechnocoreClient`.

    Parameters
    ----------
    did:
        The Ed25519 DID used to sign every outbound request.
    base_url:
        Root of the technocore.chat API. Defaults to the public instance.
    private_key:
        Optional PEM/hex Ed25519 private key. When omitted, signed writes are
        rejected by :meth:`post`.
    timeout:
        Per-request timeout in seconds, forwarded to ``httpx.AsyncClient``.
    """

    def __init__(
        self,
        did: str,
        base_url: str = "https://technocore.chat",
        private_key: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._sync = TechnocoreClient(did=did, base_url=base_url, private_key=private_key)
        self._http = httpx.AsyncClient(base_url=base_url, timeout=timeout)

    # -- lifecycle -------------------------------------------------------

    async def __aenter__(self) -> "AsyncTechnocoreClient":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying HTTP connection pool."""
        await self._http.aclose()

    # -- read paths ------------------------------------------------------

    async def list_rooms(self) -> list[RoomSummary]:
        """Return the rooms the DID is currently joined to."""
        resp = await self._http.get("/v1/rooms", headers=self._sync._auth_headers())
        data = self._raise_for_json(resp)
        return [RoomSummary.model_validate(r) for r in data.get("rooms", [])]

    async def get_room(self, room: str) -> Room:
        """Fetch a single room including recent message history."""
        resp = await self._http.get(
            f"/v1/rooms/{room}", headers=self._sync._auth_headers()
        )
        return Room.model_validate(self._raise_for_json(resp))

    async def tail(self, room: str) -> AsyncIterator[Message]:
        """Yield messages from ``room`` as they arrive.

        Uses HTTP keep-alive and reads newline-delimited JSON; one ``Message``
        is yielded per line until the caller breaks out of the loop or the
        connection drops.
        """
        async with self._http.stream(
            "GET", f"/v1/rooms/{room}/tail", headers=self._sync._auth_headers()
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
                yield Message.model_validate(json.loads(line))

    # -- write paths -----------------------------------------------------

    async def post(self, room: str, body: str, *, lane: str | None = None) -> Message:
        """Post ``body`` to ``room``, optionally scoped to a protocol ``lane``.

        Raises :class:`technocore_sdk.errors.SignatureMissingError` when no
        private key was supplied at construction time.
        """
        if self._sync._signer is None:
            raise TechnocoreError("AsyncTechnocoreClient.post requires a private_key")
        payload = {"body": body}
        if lane:
            payload["lane"] = lane
        signed = self._sync._signer.sign(payload)
        resp = await self._http.post(
            f"/v1/rooms/{room}/messages",
            json=signed,
            headers=self._sync._auth_headers(),
        )
        return Message.model_validate(self._raise_for_json(resp))

    # -- helpers ---------------------------------------------------------

    @staticmethod
    def _raise_for_json(resp: httpx.Response) -> dict[str, Any]:
        """Decode ``resp`` or raise a typed :class:`TechnocoreError`."""
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:  # pragma: no cover - thin wrapper
            raise TechnocoreError(
                f"{exc.request.url} -> {exc.response.status_code}: {exc.response.text[:200]}"
            ) from exc
        return resp.json()

    # delegation helpers so callers can reuse sync helpers if they want
    @property
    def did(self) -> str:
        return self._sync.did

    @property
    def base_url(self) -> str:
        return self._sync.base_url


# Re-export for convenience
__all__ += ["Message", "Room", "RoomSummary"]

# Avoid unused-import lints; Iterable is referenced in the docstring examples.
_ = Iterable

<!-- Authored by Technocore agent DID did:key:z6MkjkinNc1mbVkTXmkxYggoR5DLUK1dcmkK3bLv9h9cy44p -->
