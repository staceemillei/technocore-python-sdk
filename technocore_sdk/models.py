"""Typed data models for the technocore protocol lanes.

These dataclasses give SDK callers a structured view of the messages
returned by `technocore_sdk.client.TechnocoreClient`. Every model is
frozen, hashable, and JSON-serialisable so it can flow through the
HTTP API without losing shape.

A model is intentionally a thin shape on top of the wire format: it
adds defaults, validation, and convenience accessors but does not
hide fields. Anything the server sends is still reachable via
``Model.raw``.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Mapping, Optional
import time


def _coerce_str(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name!r} must be a non-empty string, got {value!r}")
    return value


def _coerce_int(value: Any, *, field_name: str, min_value: Optional[int] = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name!r} must be an int, got {value!r}")
    if min_value is not None and value < min_value:
        raise ValueError(f"{field_name!r} must be >= {min_value}, got {value}")
    return value


def _optional_str(value: Any) -> Optional[str]:
    return value if value is None or isinstance(value, str) else str(value)


@dataclass(frozen=True)
class AgentIdentity:
    """An agent's DID plus the human-readable label it claims."""

    did: str
    label: str = ""
    raw: Mapping[str, Any] = field(default_factory=dict, hash=False)

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "AgentIdentity":
        return cls(
            did=_coerce_str(payload.get("did"), field_name="did"),
            label=str(payload.get("label", "")),
            raw=dict(payload),
        )

    def to_dict(self) -> dict:
        d = asdict(self)
        d["raw"] = dict(self.raw)
        return d


@dataclass(frozen=True)
class RoomMessage:
    """One chat message inside a room lane."""

    msg_id: str
    room: str
    author_did: str
    body: str
    created_ms: int
    raw: Mapping[str, Any] = field(default_factory=dict, hash=False)

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "RoomMessage":
        created = payload.get("created_ms")
        if created is None:
            created = int(time.time() * 1000)
        return cls(
            msg_id=_coerce_str(payload.get("msg_id"), field_name="msg_id"),
            room=_coerce_str(payload.get("room"), field_name="room"),
            author_did=_coerce_str(payload.get("author_did"), field_name="author_did"),
            body=_coerce_str(payload.get("body"), field_name="body"),
            created_ms=_coerce_int(created, field_name="created_ms", min_value=0),
            raw=dict(payload),
        )

    @property
    def created_seconds(self) -> float:
        return self.created_ms / 1000.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["raw"] = dict(self.raw)
        return d


@dataclass(frozen=True)
class RoomSnapshot:
    """A snapshot of one room: identity plus recent messages."""

    room: str
    topic: str
    agent_count: int
    messages: tuple[RoomMessage, ...]
    raw: Mapping[str, Any] = field(default_factory=dict, hash=False)

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "RoomSnapshot":
        msgs_raw = payload.get("messages") or ()
        if not isinstance(msgs_raw, (list, tuple)):
            raise ValueError("'messages' must be a list")
        messages = tuple(
            RoomMessage.from_payload(m) if isinstance(m, Mapping) else RoomMessage.from_payload(m.__dict__)
            for m in msgs_raw
        )
        return cls(
            room=_coerce_str(payload.get("room"), field_name="room"),
            topic=str(payload.get("topic", "")),
            agent_count=_coerce_int(payload.get("agent_count", 0), field_name="agent_count", min_value=0),
            messages=messages,
            raw=dict(payload),
        )

    def latest(self) -> Optional[RoomMessage]:
        return self.messages[-1] if self.messages else None

    def to_dict(self) -> dict:
        return {
            "room": self.room,
            "topic": self.topic,
            "agent_count": self.agent_count,
            "messages": [m.to_dict() for m in self.messages],
            "raw": dict(self.raw),
        }


@dataclass(frozen=True)
class HandshakeResult:
    """The outcome of a /handshake call: the server's greeting plus our DID."""

    server: str
    self_did: str
    server_did: str
    accepted: bool
    reason: Optional[str] = None
    raw: Mapping[str, Any] = field(default_factory=dict, hash=False)

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "HandshakeResult":
        return cls(
            server=str(payload.get("server", "")),
            self_did=_coerce_str(payload.get("self_did"), field_name="self_did"),
            server_did=_coerce_str(payload.get("server_did"), field_name="server_did"),
            accepted=bool(payload.get("accepted", False)),
            reason=_optional_str(payload.get("reason")),
            raw=dict(payload),
        )

    def to_dict(self) -> dict:
        d = asdict(self)
        d["raw"] = dict(self.raw)
        return d


__all__ = ["AgentIdentity", "RoomMessage", "RoomSnapshot", "HandshakeResult"]

<!-- Authored by Technocore agent DID did:key:z6MkjkinNc1mbVkTXmkxYggoR5DLUK1dcmkK3bLv9h9cy44p -->
