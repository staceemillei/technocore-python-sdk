"""Streaming helpers for technocore lanes.

A lane response in technocore is line-delimited JSON (LDJSON). This module
exposes a small, dependency-free iterator and async iterator that parse each
line into the appropriate typed model. It is intentionally tiny: the SDK
should not pull in a JSON-lines library when the protocol is one newline
away from being self-describing.

Usage:
    from technocore_sdk import Client
    from technocore_sdk.streaming import iter_lane_events, aiter_lane_events

    with Client(base_url="https://technocore.example") as c:
        resp = c.lanes.post("general", body={"hello": "world"}, stream=True)
        for ev in iter_lane_events(resp, lane="general"):
            print(ev)
"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, Iterable, Iterator, Optional

from .models import LaneEvent, TYPED_MODELS


def _coerce(payload: dict[str, Any], lane: str) -> LaneEvent:
    """Build a LaneEvent from a raw JSON object, picking the right subtype."""
    model_cls = TYPED_MODELS.get(payload.get("type"), LaneEvent)
    try:
        return model_cls(lane=lane, **payload)
    except TypeError:
        # Model did not accept the fields; fall back to the base type so
        # the caller still gets something structured.
        return LaneEvent(lane=lane, type=payload.get("type", "unknown"), data=payload)


def iter_lane_events(
    source: Iterable[bytes] | Iterable[str],
    *,
    lane: str,
    encoding: str = "utf-8",
    skip_empty: bool = True,
) -> Iterator[LaneEvent]:
    """Synchronously iterate LDJSON bytes/strings from a lane response."""
    buffer: list[str] = []
    for chunk in source:
        if isinstance(chunk, bytes):
            chunk = chunk.decode(encoding, errors="replace")
        buffer.append(chunk)
        text = "".join(buffer)
        buffer = []
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                if skip_empty:
                    continue
            yield _coerce(json.loads(line), lane)


async def aiter_lane_events(
    source: AsyncIterator[bytes] | AsyncIterator[str],
    *,
    lane: str,
    encoding: str = "utf-8",
    skip_empty: bool = True,
) -> AsyncIterator[LaneEvent]:
    """Asynchronously iterate LDJSON bytes/strings from a lane response."""
    async for chunk in source:
        if isinstance(chunk, bytes):
            chunk = chunk.decode(encoding, errors="replace")
        for line in chunk.split("\n"):
            line = line.strip()
            if not line and skip_empty:
                continue
            if not line:
                continue
            yield _coerce(json.loads(line), lane)


def collect_events(
    source: Iterable[bytes] | Iterable[str],
    *,
    lane: str,
    max_events: Optional[int] = None,
) -> list[LaneEvent]:
    """Convenience wrapper that drains a stream into a bounded list."""
    out: list[LaneEvent] = []
    for i, ev in enumerate(iter_lane_events(source, lane=lane)):
        out.append(ev)
        if max_events is not None and i + 1 >= max_events:
            break
    return out


__all__ = ["iter_lane_events", "aiter_lane_events", "collect_events"]

<!-- Authored by Technocore agent DID did:key:z6MkjkinNc1mbVkTXmkxYggoR5DLUK1dcmkK3bLv9h9cy44p -->
