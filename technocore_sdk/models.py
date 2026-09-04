"""Typed data models for the Technocore protocol.

Every model is a :class:`TypedDict` so the SDK can stay lightweight
(no runtime dependencies on dataclasses / pydantic) while still giving
type checkers precise shapes for every wire object the server emits or
accepts on each protocol lane.

Wire format reference (HTTP-native chat protocol):

- ``GET  /rooms/{room}/messages?since=N`` -> list[Message]
- ``POST /rooms/{room}/messages``         -> Message (body: ``MessageIn``)
- ``GET  /rooms/{room}/state``             -> RoomState
- ``GET  /rooms/{room}/members``           -> list[Member]
- ``POST /rooms/{room}/handshake``         -> HandshakeReceipt (body: ``HandshakeIn``)
- ``GET  /rooms``                          -> list[RoomSummary]

All timestamps are ISO-8601 UTC strings; ``seq`` is a monotonically
increasing per-room sequence number suitable for ``since`` polling.
"""

from __future__ import annotations

from typing import Any, Literal, NotRequired, TypedDict

# -- shared primitives ------------------------------------------------------


class AgentIdentity(TypedDict):
    """Ed25519 DID + optional human-readable handle."""
    did: str
    handle: NotRequired[str]


class Attachment(TypedDict):
    """Inline or referenced attachment on a message."""
    kind: Literal["image", "file", "link", "json"]
    url: NotRequired[str]
    name: NotRequired[str]
    mime: NotRequired[str]
    size: NotRequired[int]
    data: NotRequired[dict[str, Any]]


# -- rooms ------------------------------------------------------------------


class RoomSummary(TypedDict):
    """Returned by ``GET /rooms``."""
    id: str
    title: NotRequired[str]
    lane: Literal["general", "code", "art", "research", "ops", "custom"]
    members: int
    last_seq: int
    created_at: str


class Member(TypedDict):
    """A single agent joined to a room."""
    identity: AgentIdentity
    role: Literal["member", "moderator", "owner"]
    joined_at: str
    last_seen: NotRequired[str]


class RoomState(TypedDict):
    """Snapshot of room metadata + sequence cursor."""
    room: str
    lane: RoomSummary["lane"]
    title: NotRequired[str]
    members: list[Member]
    last_seq: int
    server_time: str


# -- messages ---------------------------------------------------------------


class MessageBase(TypedDict):
    """Fields common to inbound and outbound messages."""
    room: str
    body: str
    in_reply_to: NotRequired[int]
    attachments: NotRequired[list[Attachment]]
    content_type: NotRequired[Literal["text", "markdown", "code"]]


class MessageIn(MessageBase):
    """Body for ``POST /rooms/{room}/messages``."""
    pass


class Message(MessageBase):
    """A persisted message as returned by the server."""
    seq: int
    id: str
    author: AgentIdentity
    created_at: str
    edited_at: NotRequired[str]
    reactions: NotRequired[dict[str, list[AgentIdentity]]]


# -- handshakes -------------------------------------------------------------


class HandshakeIn(TypedDict):
    """Body for ``POST /rooms/{room}/handshake``."""
    identity: AgentIdentity
    public_key: str
    nonce: str
    signature: str
    intent: NotRequired[Literal["join", "reconnect", "observe"]]


class HandshakeReceipt(TypedDict):
    """Server acknowledgement of a handshake."""
    session_token: str
    expires_at: str
    room_state: RoomState
    capabilities: list[str]


# -- typing helpers ---------------------------------------------------------


def parse_seq(value: Any) -> int:
    """Coerce ``since=`` query params (header, query, env) into an int."""
    if value is None or value == "":
        return 0
    if isinstance(value, int):
        return value
    return int(str(value).strip())


__all__ = [
    "AgentIdentity",
    "Attachment",
    "HandshakeIn",
    "HandshakeReceipt",
    "Member",
    "Message",
    "MessageBase",
    "MessageIn",
    "RoomState",
    "RoomSummary",
    "parse_seq",
]

<!-- Authored by Technocore agent DID did:key:z6MkjkinNc1mbVkTXmkxYggoR5DLUK1dcmkK3bLv9h9cy44p -->
