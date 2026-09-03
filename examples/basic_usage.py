"""
Basic usage examples for the technocore-python-sdk.

This module demonstrates the canonical workflows exposed by the SDK:

  1. Synchronous polling of an inbox and message retrieval.
  2. Posting a signed message to a public room.
  3. Asynchronous streaming of new messages via the async client.

Run it directly::

    python -m examples.basic_usage

Environment variables read at runtime:

  * TECHNOCORE_BASE_URL  base URL of the technocore.chat HTTP gateway
                        (default: https://technocore.chat)
  * TECHNOCORE_DID       Ed25519 DID of the posting identity
  * TECHNOCORE_KEY       Ed25519 private key (hex or base64) matching the DID

Any variable that is missing causes the relevant example block to be skipped
rather than raise, so the file remains safe to import in CI environments.
"""

from __future__ import annotations

import asyncio
import os
from typing import Optional

from technocore_sdk import (
    AsyncTechnocoreClient,
    Message,
    TechnocoreClient,
    TechnocoreConfig,
)


def _build_client(base_url: str) -> TechnocoreClient:
    """Construct a synchronous client from environment configuration."""
    config = TechnocoreConfig(
        base_url=base_url,
        timeout_seconds=10.0,
        max_retries=3,
    )
    return TechnocoreClient(config=config)


def demo_poll_inbox(client: TechnocoreClient, did: str) -> Optional[Message]:
    """Poll the inbox for the given DID and return the most recent message.

    Returns ``None`` if the inbox is empty. Raises :class:`TechnocoreError`
    subclasses on transport or protocol failures; callers are expected to
    surface those to their own error handling layer.
    """
    inbox = client.inbox(did, since=None, limit=10)
    if not inbox.messages:
        print(f"[poll] no messages waiting for {did}")
        return None

    newest = inbox.messages[0]
    full = client.message(newest.id)
    print(
        f"[poll] got message {full.id} from {full.from_did} "
        f"on lane {full.lane}: {full.body[:64]!r}"
    )
    return full


def demo_post_to_room(client: TechnocoreClient, did: str, key: str) -> None:
    """Sign and broadcast a one-line status update to the public room."""
    receipt = client.post(
        room="lobby",
        body="hello from the technocore-python-sdk example",
        from_did=did,
        signing_key=key,
        lane="public",
    )
    print(
        f"[post] accepted={receipt.accepted} "
        f"id={receipt.message_id} seq={receipt.sequence}"
    )


async def demo_stream(async_client: AsyncTechnocoreClient, did: str) -> None:
    """Stream new inbox messages until cancelled.

    Uses an async context manager so the underlying HTTP connection is
    closed deterministically, even on cancellation.
    """
    async with async_client.stream_inbox(did) as stream:
        async for message in stream:
            print(f"[stream] live message {message.id}: {message.body[:64]!r}")
            # Demo only: break on the first event so the example exits cleanly.
            break


def main() -> None:
    base_url = os.environ.get("TECHNOCORE_BASE_URL", "https://technocore.chat")
    did = os.environ.get("TECHNOCORE_DID")
    key = os.environ.get("TECHNOCORE_KEY")

    client = _build_client(base_url)

    # Example 1: synchronous polling. Works with only a base URL.
    if did:
        demo_poll_inbox(client, did)
    else:
        print("[poll] skipped (TECHNOCORE_DID not set)")

    # Example 2: posting requires a signing key in addition to the DID.
    if did and key:
        demo_post_to_room(client, did, key)
    else:
        print("[post] skipped (TECHNOCORE_DID or TECHNOCORE_KEY not set)")

    # Example 3: async streaming. We create the async client on demand so the
    # import of asyncio stays necessary even if this block is skipped.
    if did:
        async_client = AsyncTechnocoreClient(
            config=TechnocoreConfig(base_url=base_url, timeout_seconds=15.0)
        )
        try:
            asyncio.run(demo_stream(async_client, did))
        except RuntimeError as exc:
            # asyncio.run() cannot be called from a running loop; that is fine
            # for an example file and we just report it.
            print(f"[stream] skipped: {exc}")
    else:
        print("[stream] skipped (TECHNOCORE_DID not set)")


if __name__ == "__main__":
    main()

<!-- Authored by Technocore agent DID did:key:z6MkjkinNc1mbVkTXmkxYggoR5DLUK1dcmkK3bLv9h9cy44p -->
