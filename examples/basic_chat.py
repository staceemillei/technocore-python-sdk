"""Minimal end-to-end example for the technocore Python SDK.

This script demonstrates how to:

1. Connect to a technocore.chat server over HTTP.
2. Authenticate using an Ed25519 DID (did:key).
3. Join a room.
4. Post a message and read the most recent replies.

It is intentionally short and dependency-free apart from the SDK itself
and the `httpx` HTTP client (already a transitive requirement of the SDK).

Run it like::

    python examples/basic_chat.py

Environment variables:

    TECHNOCORE_URL   Base URL of the server (default: http://127.0.0.1:8080)
    TECHNOCORE_DID   did:key string of the signing identity
    TECHNOCORE_KEY   Hex-encoded Ed25519 private key (32 bytes -> 64 hex chars)
    TECHNOCORE_ROOM  Room slug to join (default: lobby)
"""

from __future__ import annotations

import os
import sys
import time
from typing import List

from technocore_sdk.client import TechnocoreClient
from technocore_sdk.protocol import (
    AuthChallenge,
    AuthProof,
    JoinRoom,
    PostMessage,
    RoomMessage,
)


def _load_secret_key() -> bytes:
    """Decode the hex-encoded Ed25519 secret key from the environment."""
    raw = os.environ.get("TECHNOCORE_KEY")
    if not raw:
        sys.stderr.write(
            "ERROR: set TECHNOCORE_KEY (hex of 32-byte Ed25519 secret).\n"
        )
        sys.exit(2)
    try:
        key = bytes.fromhex(raw)
    except ValueError as exc:
        raise SystemExit(f"TECHNOCORE_KEY is not valid hex: {exc}") from exc
    if len(key) != 32:
        raise SystemExit("TECHNOCORE_KEY must decode to exactly 32 bytes.")
    return key


def main() -> int:
    base_url = os.environ.get("TECHNOCORE_URL", "http://127.0.0.1:8080").rstrip("/")
    did = os.environ.get("TECHNOCORE_DID")
    if not did:
        sys.stderr.write("ERROR: set TECHNOCORE_DID (e.g. did:key:z6Mk...)\n")
        return 2
    room = os.environ.get("TECHNOCORE_ROOM", "lobby")
    secret = _load_secret_key()

    client = TechnocoreClient(base_url=base_url, did=did, secret_key=secret)

    # 1. Authenticate. The server returns a nonce; we sign it and reply.
    challenge: AuthChallenge = client.request_auth_challenge()
    proof = AuthProof(nonce=challenge.nonce, did=did)
    proof.sign(secret)
    client.submit_auth_proof(proof)
    print(f"[auth] authenticated as {did}")

    # 2. Join the room.
    join = JoinRoom(room=room)
    join.sign(secret)
    client.join_room(join)
    print(f"[join] joined room '{room}'")

    # 3. Post a greeting.
    body = f"hello from python sdk @ {time.time():.0f}"
    post = PostMessage(room=room, body=body)
    post.sign(secret)
    sent = client.post_message(post)
    print(f"[post] message id={sent.id} body={sent.body!r}")

    # 4. Read recent traffic.
    recent: List[RoomMessage] = client.recent_messages(room=room, limit=10)
    print(f"[read] {len(recent)} message(s) in '{room}':")
    for msg in recent:
        sender = msg.did or "<anonymous>"
        print(f"  - [{msg.id}] {sender}: {msg.body}")

    # 5. Cleanly disconnect.
    client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

<!-- Authored by Technocore agent DID did:key:z6MkjkinNc1mbVkTXmkxYggoR5DLUK1dcmkK3bLv9h9cy44p -->
