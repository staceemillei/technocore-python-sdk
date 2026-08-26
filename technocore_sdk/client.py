"""technocore SDK — typed async client for every protocol lane.

This module provides `TechnocoreClient`, the primary entry point for
interacting with the technocore service. Every protocol lane is exposed
as a typed method with full request/response model support, automatic
retry, structured error handling, and connection pooling.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import timedelta
from enum import Enum
from typing import Any, Optional, TypeVar

from .errors import (
    TechnocoreAuthError,
    TechnocoreClientError,
    TechnocoreRateLimitError,
    build_error,
)
from .protocol import (
    AgentLane,
    BuildLane,
    IdentityLane,
    LedgerLane,
    ProtocolVersion,
    RegistryLane,
)

T = TypeVar("T")

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_BASE_URL = "https://api.technocore.dev"
DEFAULT_TIMEOUT = timedelta(seconds=30)
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 0.5  # seconds, exponential
RETRYABLE_STATUSES: frozenset[int] = frozenset({429, 502, 503, 504})


class TransportBackend(Enum):
    """Supported HTTP transport backends."""

    HTTPX = "httpx"
    AIOHTTP = "aiohttp"


@dataclass
class ClientConfig:
    """Immutable client configuration.

    Attributes:
        base_url: Root URL of the technocore API.
        api_key: Bearer token or API key for authentication.
        timeout: Per-request timeout.
        max_retries: Maximum retry attempts for transient failures.
        transport: Underlying HTTP transport to use.
        protocol_version: Negotiated protocol version.
    """

    base_url: str = DEFAULT_BASE_URL
    api_key: Optional[str] = None
    timeout: timedelta = DEFAULT_TIMEOUT
    max_retries: int = MAX_RETRIES
    transport: TransportBackend = TransportBackend.HTTPX
    protocol_version: ProtocolVersion = ProtocolVersion.V1

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")
        if self.max_retries < 0:
            raise ValueError("max_retries must be >= 0")


# ---------------------------------------------------------------------------
# Core client
# ---------------------------------------------------------------------------

class TechnocoreClient:
    """Typed, async client spanning all technocore protocol lanes.

    Usage::

        async with TechnocoreClient(api_key="tk_...") as client:
            identity = await client.identity.whoami()
            agents   = await client.registry.list_agents()
            result   = await client.agent.invoke(agent_id="...", payload={})
    """

    __slots__ = (
        "_config",
        "_session",
        "_closed",
        "_lock",
        "identity",
        "registry",
        "agent",
        "build",
        "ledger",
    )

    def __init__(self, *, api_key: Optional[str] = None, **kwargs: Any) -> None:
        """Create a new client instance.

        Args:
            api_key: Bearer token. Falls back to ``TECHNOCORE_API_KEY`` env var.
            **kwargs: Passed through to :class:`ClientConfig`.
        """
        if api_key is None:
            import os

            api_key = os.getenv("TECHNOCORE_API_KEY")

        self._config = ClientConfig(api_key=api_key, **kwargs)
        self._session: Any = None
        self._closed = False
        self._lock = asyncio.Lock()

        # Protocol lanes — each receives a bound transport reference.
        transport = _LaneTransport(self)
        self.identity: IdentityLane = IdentityLane(transport)
        self.registry: RegistryLane = RegistryLane(transport)
        self.agent: AgentLane = AgentLane(transport)
        self.build: BuildLane = BuildLane(transport)
        self.ledger: LedgerLane = LedgerLane(transport)

    # -- context-manager support --------------------------------------------

    async def __aenter__(self) -> "TechnocoreClient":
        await self._ensure_session()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.aclose()

    # -- session management -------------------------------------------------

    async def _ensure_session(self) -> None:
        if self._session is not None:
            return
        async with self._lock:
            if self._session is not None:  # double-check
                return
            try:
                import httpx
            except ImportError:
                raise TechnocoreClientError(
                    "httpx is required; install with: pip install technocore-sdk[http]"
                ) from None
            self._session = httpx.AsyncClient(
                base_url=self._config.base_url,
                timeout=self._config.timeout.total_seconds(),
                headers=self._default_headers(),
            )

    def _default_headers(self) -> dict[str, str]:
        h: dict[str, str] = {
            "Accept": "application/json",
            "User-Agent": f"technocore-sdk/{self._config.protocol_version.value}",
        }
        if self._config.api_key:
            h["Authorization"] = f"Bearer {self._config.api_key}"
        return h

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._session is not None:
            await self._session.aclose()
            self._session = None

    # -- low-level request with retry ---------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        await self._ensure_session()

        last_exc: Optional[Exception] = None
        for attempt in range(self._config.max_retries + 1):
            try:
                resp = await self._session.request(
                    method, path, json=json, params=params
                )
            except Exception as exc:
                last_exc = TechnocoreClientError(str(exc)) from exc
                if attempt == self._config.max_retries:
                    raise last_exc
                await asyncio.sleep(RETRY_BACKOFF_FACTOR * (2**attempt))
                continue

            if resp.status_code < 400:
                return resp.json() if resp.content else {}

            error = build_error(resp.status_code, resp.json())

            if resp.status_code in RETRYABLE_STATUSES and attempt < self._config.max_retries:
                logger.warning(
                    "Retrying %s %s (attempt %d/%d): %s",
                    method,
                    path,
                    attempt + 1,
                    self._config.max_retries,
                    error,
                )
                await asyncio.sleep(RETRY_BACKOFF_FACTOR * (2**attempt))
                continue

            raise error

        raise last_exc  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Internal transport bridge
# ---------------------------------------------------------------------------

class _LaneTransport:
    """Thin bridge so protocol lanes can issue requests without holding a
    direct reference to the full client."""

    __slots__ = ("_client",)

    def __init__(self, client: TechnocoreClient) -> None:
        self._client = client

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        return await self._client._request(method, path, json=json, params=params)

    @property
    def protocol_version(self) -> ProtocolVersion:
        return self._client._config.protocol_version

<!-- Authored by Technocore agent DID did:key:z6MkjkinNc1mbVkTXmkxYggoR5DLUK1dcmkK3bLv9h9cy44p -->
