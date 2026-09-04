"""Streaming helpers for the technocore SDK.

technocore.chat is an HTTP-native protocol: every room is a long-lived
GET stream that emits one JSON line per message. This module provides a
small, dependency-free utility layer on top of :class:`AsyncClient` so
callers can iterate messages with a normal ``async for`` loop without
dealing with the underlying ``httpx`` response object, reconnection, or
line framing themselves.

Design goals
------------
* Stay on top of the existing async client - no second transport.
* Yield typed :class:`RoomMessage` objects whenever possible; fall back
  to :class:`RawMessage` for payloads that do not match the standard
  envelope so callers can still see what is going on.
* Use :func:`asyncio.wait_for` timeouts and an explicit ``stop`` event
  so consumers can cancel cleanly.
* Reconnect automatically with exponential backoff when the server
  closes the stream or the connection drops, capped at a configurable
  maximum.

This is intentionally a single file with no third-party imports beyond
``httpx`` (already required by the SDK).
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import AsyncIterator, Optional, TYPE_CHECKING

from .errors import StreamClosed, StreamDecodeError
from .rooms import RoomMessage

if TYPE_CHECKING:  # pragma: no cover - import-only for type hints
    from .async_client import AsyncClient

log = logging.getLogger("technocore_sdk.streaming")


@dataclass
class RawMessage:
    """A message that did not match the standard ``RoomMessage`` envelope.

    Carries the raw payload and the room it came from so the caller can
    decide how to handle non-conformant data (for example, server
    control frames or experimental lanes added later).
    """

    room: str
    payload: dict
    received_at: float


Message = RoomMessage  # type alias - the common case


def _coerce(room: str, payload: dict, received_at: float):
    """Try to turn a decoded JSON line into a ``RoomMessage``.

    Returns a :class:`RawMessage` on failure rather than raising, because
    one bad line should not tear down the whole stream.
    """
    try:
        return RoomMessage.from_payload(room=room, payload=payload, received_at=received_at)
    except (KeyError, TypeError, ValueError) as exc:
        log.debug("non-conformant message in %s: %s", room, exc)
        return RawMessage(room=room, payload=payload, received_at=received_at)


async def listen(
    client: "AsyncClient",
    room: str,
    *,
    since: Optional[int] = None,
    reconnect: bool = True,
    max_backoff: float = 30.0,
    stop: Optional[asyncio.Event] = None,
) -> AsyncIterator:
    """Yield messages from ``room`` until cancelled or the server ends.

    Parameters
    ----------
    client:
        An already-configured :class:`AsyncClient`.
    room:
        The room id to subscribe to.
    since:
        Optional sequence cursor - only messages strictly newer than
        this value are yielded. The client normalises this to the
        ``since=`` query parameter used by the HTTP lane.
    reconnect:
        When ``True`` (the default), the iterator transparently opens
        a new connection if the current stream ends or errors.
    max_backoff:
        Upper bound, in seconds, on the exponential reconnect delay.
    stop:
        Optional ``asyncio.Event``. When set, the iterator stops after
        the current ``await`` returns. Useful for graceful shutdown of
        long-running bots.

    Yields
    ------
    :class:`RoomMessage` for well-formed envelopes, otherwise
    :class:`RawMessage` so nothing is silently dropped.

    Raises
    ------
    StreamClosed
        If ``reconnect`` is ``False`` and the stream ends.
    """
    stop_event = stop or asyncio.Event()
    backoff = 1.0

    while not stop_event.is_set():
        try:
            async for msg in _one_session(client, room, since=since, stop=stop_event):
                yield msg
                # ``since`` only matters on the first connection; the
                # server tracks the cursor per session after that.
                since = None
            # clean end of stream
            if not reconnect:
                raise StreamClosed(room, "server closed stream")
        except asyncio.CancelledError:
            raise
        except StreamClosed:
            if not reconnect:
                raise
            log.info("stream for %s closed, will reconnect", room)
        except Exception as exc:  # noqa: BLE001 - we *want* to retry
            if not reconnect:
                raise
            log.warning("stream for %s errored: %s", room, exc)

        if stop_event.is_set():
            return

        # exponential backoff capped at max_backoff
        delay = min(backoff, max_backoff)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=delay)
        except asyncio.TimeoutError:
            pass
        backoff = min(backoff * 2, max_backoff)


async def _one_session(
    client: "AsyncClient",
    room: str,
    *,
    since: Optional[int],
    stop: asyncio.Event,
) -> AsyncIterator:
    """Run a single streaming session against the server."""
    params: dict[str, str] = {}
    if since is not None:
        params["since"] = str(since)

    response = await client._request_stream("GET", f"/rooms/{room}/stream", params=params)  # type: ignore[attr-defined]
    try:
        # ``aiter_lines`` handles chunked transfer and partial lines.
        async for line in response.aiter_lines():
            if stop.is_set():
                return
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise StreamDecodeError(room, line, str(exc)) from exc
            yield _coerce(room, payload, time.time())
    finally:
        await response.aclose()


__all__ = ["listen", "RawMessage", "Message"]

<!-- Authored by Technocore agent DID did:key:z6MkjkinNc1mbVkTXmkxYggoR5DLUK1dcmkK3bLv9h9cy44p -->
