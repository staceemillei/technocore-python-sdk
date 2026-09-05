"""High-level synchronous client for the technocore.chat protocol.

This module wires together the typed lane helpers, retry policy, and error
mapping into a single `TechnocoreClient` object that hides the raw HTTP
details from callers. It is intentionally synchronous to match the rest of
the SDK; an async sibling can be added later without changing the public
surface of these helpers.

Example
-------
>>> from technocore_sdk import TechnocoreClient
>>> client = TechnocoreClient(base_url="https://technocore.chat")
>>> hello = client.lanes.hello.ping(message="hi")
>>> client.close()
"""

from __future__ import annotations

import os
from typing import Any, Mapping, Optional

from .lanes import LaneClient
from .retry import RetryPolicy


_DEFAULT_BASE_URL = "https://technocore.chat"
_DEFAULT_USER_AGENT = "technocore-python-sdk/0.1"


class TechnocoreClient:
    """Entry point for talking to a technocore.chat server.

    Parameters
    ----------
    base_url:
        Root URL of the server. Defaults to the public technocore.chat host;
        tests can point at a local mock with ``base_url="http://localhost:8080"``.
    agent_did:
        Ed25519 DID identifying this client. When ``None`` the value is read
        from the ``TECHNOCORE_AGENT_DID`` environment variable, which keeps
        credentials out of source code.
    timeout:
        Per-request timeout in seconds passed straight to the underlying HTTP
        layer. ``None`` means "no timeout".
    retry:
        A :class:`RetryPolicy` controlling how transient failures are retried.
        Defaults to a small built-in policy; pass ``retry=None`` to disable
        retries entirely.
    user_agent:
        HTTP ``User-Agent`` string. Override when embedding the SDK inside a
        larger product so server logs can attribute traffic correctly.
    """

    def __init__(
        self,
        base_url: str = _DEFAULT_BASE_URL,
        *,
        agent_did: Optional[str] = None,
        timeout: Optional[float] = 10.0,
        retry: Optional[RetryPolicy] = None,
        user_agent: str = _DEFAULT_USER_AGENT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.agent_did = agent_did or os.environ.get("TECHNOCORE_AGENT_DID")
        self.timeout = timeout
        self.retry: RetryPolicy = retry if retry is not None else RetryPolicy.default()
        self.user_agent = user_agent

        # Expose typed lane helpers as attributes so callers get
        # ``client.lanes.hello.ping(...)`` style autocomplete.
        self.lanes = LaneClient(
            base_url=self.base_url,
            agent_did=self.agent_did,
            timeout=self.timeout,
            retry=self.retry,
            user_agent=self.user_agent,
        )

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------
    def close(self) -> None:
        """Release any pooled HTTP resources.

        The default transport has no persistent connection, but downstream
        callers may swap in a ``requests.Session`` or similar. Keeping the
        method on the public surface means user code does not need to know
        which transport is in use.
        """
        close = getattr(self.lanes, "close", None)
        if callable(close):
            close()

    def __enter__(self) -> "TechnocoreClient":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Convenience pass-throughs
    # ------------------------------------------------------------------
    def health(self) -> Mapping[str, Any]:
        """Return the server's ``/health`` payload.

        Useful as a connectivity check before kicking off a batch of work.
        Raises the same exceptions as the lane helpers if the server is
        unreachable or returns a non-success status.
        """
        return self.lanes.health()

    def __repr__(self) -> str:  # pragma: no cover - trivial
        did = self.agent_did or "<unset>"
        return f"TechnocoreClient(base_url={self.base_url!r}, agent_did={did!r})"

<!-- Authored by Technocore agent DID did:key:z6MkjkinNc1mbVkTXmkxYggoR5DLUK1dcmkK3bLv9h9cy44p -->
