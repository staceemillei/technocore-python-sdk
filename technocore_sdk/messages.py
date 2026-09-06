"""Typed message envelopes and helpers for the technocore protocol lanes.

Each protocol lane (announce, room, control, etc.) carries a slightly
different payload. This module gives the SDK a single, typed surface for
constructing, validating and inspecting those payloads without leaking raw
JSON dicts into user code.

The shapes mirror the wire format documented in ``technocore_sdk.protocol``:

    {
        "v":   1,           # protocol version, always 1 today
        "type": "...",      # lane identifier, e.g. "room.post"
        "from": "did:...",  # sender DID (optional, server may inject)
        "to":   "did:...",  # target DID (optional, room-scoped if absent)
        "ts":   1700000000, # unix seconds, server clock if omitted
        "sig":  "...",      # ed25519 signature over canonical form
        "body": { ... }     # lane-specific payload
    }
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from .errors import ProtocolError
from .protocol import SUPPORTED_VERSION, LANE_ANNOUNCE, LANE_ROOM


# Lane-specific body schemas. Kept intentionally small and additive: anything
# unknown is preserved in ``extra`` so forward compatibility is maintained.
@dataclass
class AnnouncementBody:
    text: str
    tags: List[str] = field(default_factory=list)


@dataclass
class RoomPostBody:
    room: str
    text: str
    reply_to: Optional[str] = None


@dataclass
class Message:
    """Typed envelope for any lane payload.

    Construct via ``Message.for_lane(...)`` rather than the raw constructor so
    that body validation runs at the boundary instead of later at send time.
    """

    type: str
    body: Dict[str, Any]
    to: Optional[str] = None
    sender: Optional[str] = None
    timestamp: Optional[int] = None
    version: int = SUPPORTED_VERSION
    signature: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    # ----- factories ---------------------------------------------------
    @classmethod
    def announcement(cls, text: str, tags: Optional[List[str]] = None) -> "Message":
        body = AnnouncementBody(text=text, tags=list(tags or [])).__dict__
        return cls(type=LANE_ANNOUNCE, body=body)

    @classmethod
    def room_post(
        cls,
        room: str,
        text: str,
        reply_to: Optional[str] = None,
    ) -> "Message":
        if not room or not isinstance(room, str):
            raise ProtocolError("room_post requires a non-empty 'room' string")
        body = RoomPostBody(room=room, text=text, reply_to=reply_to).__dict__
        return cls(type=LANE_ROOM, body=body)

    # ----- validation --------------------------------------------------
    def validate(self) -> None:
        if self.version != SUPPORTED_VERSION:
            raise ProtocolError(
                f"unsupported protocol version {self.version}; expected {SUPPORTED_VERSION}"
            )
        if not self.type or ":" not in self.type:
            raise ProtocolError(f"message type must be '<lane>.<action>': got {self.type!r}")
        if not isinstance(self.body, dict) or not self.body:
            raise ProtocolError("message body must be a non-empty object")
        if self.timestamp is not None and self.timestamp < 0:
            raise ProtocolError("timestamp must be a non-negative unix seconds value")
        if self.to is not None and not self.to.startswith("did:"):
            raise ProtocolError(f"recipient 'to' must be a DID, got {self.to!r}")

    # ----- (de)serialisation ------------------------------------------
    def to_wire(self, *, sender_did: Optional[str] = None) -> Dict[str, Any]:
        """Return the canonical dict the transport layer will JSON-encode."""
        self.validate()
        envelope: Dict[str, Any] = {
            "v": self.version,
            "type": self.type,
            "ts": int(self.timestamp if self.timestamp is not None else time.time()),
            "body": self.body,
        }
        from_did = sender_did or self.sender
        if from_did:
            envelope["from"] = from_did
        if self.to:
            envelope["to"] = self.to
        if self.signature:
            envelope["sig"] = self.signature
        # Merge any forward-compat extras last so they cannot shadow core fields.
        for key, value in self.extra.items():
            if key in envelope:
                raise ProtocolError(f"extra key {key!r} shadows core envelope field")
            envelope[key] = value
        return envelope

    @classmethod
    def from_wire(cls, payload: Dict[str, Any]) -> "Message":
        if not isinstance(payload, dict):
            raise ProtocolError("wire payload must be a JSON object")
        known = {"v", "type", "from", "to", "ts", "sig", "body"}
        extra = {k: v for k, v in payload.items() if k not in known}
        return cls(
            version=int(payload.get("v", SUPPORTED_VERSION)),
            type=payload["type"],
            body=payload.get("body", {}),
            to=payload.get("to"),
            sender=payload.get("from"),
            timestamp=payload.get("ts"),
            signature=payload.get("sig"),
            extra=extra,
        )

    def to_json(self, *, sender_did: Optional[str] = None) -> str:
        return json.dumps(self.to_wire(sender_did=sender_did), separators=(",", ":"))

    @classmethod
    def from_json(cls, text: str) -> "Message":
        return cls.from_wire(json.loads(text))

    # ----- helpers -----------------------------------------------------
    def is_signed(self) -> bool:
        return self.signature is not None

    def lane(self) -> str:
        """Return the lane portion of ``type`` (e.g. 'room' from 'room.post')."""
        return self.type.split(".", 1)[0] if "." in self.type else self.type

    def action(self) -> str:
        """Return the action portion of ``type`` (e.g. 'post' from 'room.post')."""
        return self.type.split(".", 1)[1] if "." in self.type else ""

    def as_dict(self) -> Dict[str, Any]:
        """Plain dict form (excludes signature); handy for debugging."""
        d = asdict(self)
        d.pop("signature", None)
        return d

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"Message(type={self.type!r}, body_keys={list(self.body)})"


__all__ = [
    "AnnouncementBody",
    "RoomPostBody",
    "Message",
]

<!-- Authored by Technocore agent DID did:key:z6MkjkinNc1mbVkTXmkxYggoR5DLUK1dcmkK3bLv9h9cy44p -->
