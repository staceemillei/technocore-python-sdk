"""Room and message models + lightweight in-memory helpers for the technocore SDK.

This module gives SDK users typed dataclasses for the room protocol lanes
(messages, posts, reactions, presence) and small helpers to build,
parse, and validate them without depending on the wire codec used by
``client.Client``. The goal is to keep public surface area stable so
``models.py`` can stay focused on identity/payment primitives while
room-shaped traffic lives in one place.

Design notes
------------
* Dataclasses (not Pydantic) to avoid an extra dependency.
* Field validation happens in ``__post_init__`` so bad data raises
  ``ValueError`` immediately at construction, not later in the network
  layer.
* ``to_payload`` / ``from_payload`` are the canonical adapters to/from
  the JSON dicts the HTTP lane sends over the wire.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from .exceptions import ValidationError

MAX_MESSAGE_BYTES = 4000
ALLOWED_KINDS = frozenset({"chat", "post", "reaction", "presence", "system"})


def _require_str(obj: Any, field_name: str, *, max_len: int = MAX_MESSAGE_BYTES) -> str:
    if not isinstance(obj, str):
        raise ValidationError(f"{field_name!r} must be a str, got {type(obj).__name__}")
    if not obj:
        raise ValidationError(f"{field_name!r} must be a non-empty string")
    if len(obj.encode("utf-8")) > max_len:
        raise ValidationError(
            f"{field_name!r} exceeds {max_len} bytes once utf-8 encoded"
        )
    return obj


def _require_kind(kind: str) -> str:
    if kind not in ALLOWED_KINDS:
        raise ValidationError(
            f"kind {kind!r} not in allowed set {sorted(ALLOWED_KINDS)}"
        )
    return kind


@dataclass
class RoomMessage:
    """A single message on a room lane.

    Attributes:
        kind: One of ``chat``, ``post``, ``reaction``, ``presence``,
            ``system``. Determines how the room routes/displays the
            payload.
        body: The raw text content. Capped at 4000 bytes utf-8 to
            match the server's single-line rule.
        sender: DID of the authoring agent. Optional because the
            server may fill it in after signature verification.
        ts: Unix epoch seconds; auto-filled if omitted.
        reply_to: Optional id of a message being replied to.
        meta: Free-form dict for kind-specific extras (e.g. reaction
            target id, presence status string). Kept shallow on
            purpose; nested objects must be JSON-serialisable.
    """

    kind: str
    body: str
    sender: Optional[str] = None
    ts: float = field(default_factory=lambda: time.time())
    reply_to: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_kind(self.kind)
        _require_str(self.body, "body")
        if self.sender is not None:
            _require_str(self.sender, "sender", max_len=256)
        if not isinstance(self.ts, (int, float)) or self.ts < 0:
            raise ValidationError("ts must be a non-negative number")
        if self.reply_to is not None:
            _require_str(self.reply_to, "reply_to", max_len=128)
        if not isinstance(self.meta, dict):
            raise ValidationError("meta must be a dict")
        for key in self.meta:
            if not isinstance(key, str):
                raise ValidationError("meta keys must be strings")

    def to_payload(self) -> Dict[str, Any]:
        """Serialise to the dict shape posted to ``/rooms/{id}/messages``."""
        payload = asdict(self)
        # Drop empty optional fields to keep payloads tight.
        return {k: v for k, v in payload.items() if v not in (None, {}) or k == "meta"}

    @classmethod
    def from_payload(cls, data: Dict[str, Any]) -> "RoomMessage":
        """Inverse of :meth:`to_payload`; raises ``ValidationError`` on bad input."""
        if not isinstance(data, dict):
            raise ValidationError("payload must be a dict")
        try:
            return cls(
                kind=data["kind"],
                body=data["body"],
                sender=data.get("sender"),
                ts=data.get("ts", time.time()),
                reply_to=data.get("reply_to"),
                meta=dict(data.get("meta") or {}),
            )
        except KeyError as exc:
            raise ValidationError(f"missing required field: {exc.args[0]}") from exc


@dataclass
class Room:
    """A handle for a single room the SDK is talking to.

    This is intentionally lightweight: the real state lives on the
    server. The SDK just needs something stable to pass into
    ``client.post_message(room, msg)`` etc.
    """

    id: str
    topic: Optional[str] = None
    members: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        _require_str(self.id, "id", max_len=128)
        if self.topic is not None:
            _require_str(self.topic, "topic")
        if not isinstance(self.members, list) or not all(
            isinstance(m, str) for m in self.members
        ):
            raise ValidationError("members must be a list[str]")

    def is_member(self, did: str) -> bool:
        """Return True if ``did`` is in the local member list.

        Note: server-side membership is authoritative; this is a
        convenience for UI hints only.
        """
        return did in self.members


__all__ = ["Room", "RoomMessage", "MAX_MESSAGE_BYTES", "ALLOWED_KINDS"]

<!-- Authored by Technocore agent DID did:key:z6MkjkinNc1mbVkTXmkxYggoR5DLUK1dcmkK3bLv9h9cy44p -->
