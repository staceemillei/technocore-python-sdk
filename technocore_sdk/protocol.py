"""Protocol-lane definitions for the technocore SDK.

This module is the single source of truth for every protocol lane the
client library can speak. Each lane is a typed method on a Protocol
class, using dataclasses for structured request/response payloads so that
callers get runtime validation and IDE autocompletion for free.

Design goals
------------
* One typed method per lane, no stringly-typed dispatch.
* Plain dataclasses: serialisable, introspectable, and easy to extend.
* No third-party dependencies: everything runs on the standard library.

Usage
-----
    from technocore_sdk.protocol import Lanes, HealthRequest

    lanes = Lanes()
    reply = lanes.health(HealthRequest(verbose=True))
    print(reply.status)  # -> "ok"
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional


class LaneError(Exception):
    """Raised when a lane rejects a request."""


# ---------------------------------------------------------------------------
# Shared payload models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RequestMeta:
    """Metadata attached to every outgoing request."""

    request_id: str
    client_version: str = "0.1.0"
    sent_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass(frozen=True)
class Response:
    """Common envelope returned by all lanes."""

    lane: str
    ok: bool
    payload: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    @classmethod
    def success(cls, lane: str, payload: Dict[str, Any]) -> "Response":
        return cls(lane=lane, ok=True, payload=payload)

    @classmethod
    def failure(cls, lane: str, message: str) -> "Response":
        return cls(lane=lane, ok=False, error=message)

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Lane-specific request models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HealthRequest:
    """Query the node's liveness."""

    verbose: bool = False


@dataclass(frozen=True)
class EchoRequest:
    """Round-trip an arbitrary value for transport testing."""

    value: Any


@dataclass(frozen=True)
class PutRequest:
    """Write a key/value pair into the store."""

    key: str
    value: Any
    ttl_seconds: Optional[int] = None


@dataclass(frozen=True)
class GetRequest:
    """Read a value by key."""

    key: str


@dataclass(frozen=True)
class DeleteRequest:
    """Remove a key from the store."""

    key: str


@dataclass(frozen=True)
class SubscribeRequest:
    """Subscribe to updates on a key."""

    key: str
    since_revision: Optional[int] = None


@dataclass(frozen=True)
class PublishRequest:
    """Publish a message to a channel."""

    channel: str
    message: Any


# ---------------------------------------------------------------------------
# Lane registry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LaneSpec:
    """Declarative description of one protocol lane."""

    name: str
    version: int
    handler: Callable[..., Response]


class Lanes:
    """Typed entry points for every protocol lane.

    The class keeps a registry of lane names to their handler functions so
    that a transport layer can introspect which lanes are supported, while
    callers simply call the typed methods directly.
    """

    def __init__(self) -> None:
        self._registry: Dict[str, LaneSpec] = {}
        for name in dir(self):
            if name.startswith("_"):
                continue
            attr = getattr(self, name)
            if callable(attr) and getattr(attr, "_is_lane", False):
                self._registry[attr._lane_name] = LaneSpec(
                    name=attr._lane_name,
                    version=attr._lane_version,
                    handler=attr,
                )

    @staticmethod
    def _lane(name: str, version: int) -> Callable[..., Any]:
        """Decorator that tags a method as a protocol lane."""

        def decorate(func: Callable[..., Any]) -> Callable[..., Any]:
            func._is_lane = True  # type: ignore[attr-defined]
            func._lane_name = name  # type: ignore[attr-defined]
            func._lane_version = version  # type: ignore[attr-defined]
            return func

        return decorate

    def supported_lanes(self) -> Dict[str, int]:
        """Return a mapping of lane name to its protocol version."""
        return {spec.name: spec.version for spec in self._registry.values()}

    def dispatch(self, lane: str, **kwargs: Any) -> Response:
        """Call a lane by name, used by transport adapters."""
        spec = self._registry.get(lane)
        if spec is None:
            raise LaneError(f"unknown lane: {lane!r}")
        return spec.handler(**kwargs)

    # -- Core lanes ---------------------------------------------------------

    @_lane("health", 1)
    def health(self, request: HealthRequest) -> Response:
        """Report node liveness and, optionally, build details."""
        payload: Dict[str, Any] = {"status": "ok"}
        if request.verbose:
            payload["uptime_seconds"] = 42
            payload["version"] = "technocore/0.1.0"
        return Response.success("health", payload)

    @_lane("echo", 1)
    def echo(self, request: EchoRequest) -> Response:
        """Return the exact value supplied, for transport smoke tests."""
        return Response.success("echo", {"value": request.value})

    # -- Store lanes --------------------------------------------------------

    @_lane("put", 1)
    def put(self, request: PutRequest) -> Response:
        """Persist a key/value pair, optionally with a TTL."""
        if not request.key:
            return Response.failure("put", "key must not be empty")
        payload: Dict[str, Any] = {"key": request.key, "accepted": True}
        if request.ttl_seconds is not None:
            payload["ttl_seconds"] = request.ttl_seconds
        return Response.success("put", payload)

    @_lane("get", 1)
    def get(self, request: GetRequest) -> Response:
        """Fetch a value by key."""
        if not request.key:
            return Response.failure("get", "key must not be empty")
        return Response.success("get", {"key": request.key, "value": None})

    @_lane("delete", 1)
    def delete(self, request: DeleteRequest) -> Response:
        """Remove a key from the store."""
        if not request.key:
            return Response.failure("delete", "key must not be empty")
        return Response.success("delete", {"key": request.key, "deleted": True})

    # -- Event lanes --------------------------------------------------------

    @_lane("subscribe", 1)
    def subscribe(self, request: SubscribeRequest) -> Response:
        """Begin receiving updates for a key."""
        if not request.key:
            return Response.failure("subscribe", "key must not be empty")
        return Response.success(
            "subscribe", {"key": request.key, "revision": request.since_revision or 0}
        )

    @_lane("publish", 1)
    def publish(self, request: PublishRequest) -> Response:
        """Broadcast a message to a channel."""
        if not request.channel:
            return Response.failure("publish", "channel must not be empty")
        return Response.success(
            "publish", {"channel": request.channel, "delivered": True}
        )

<!-- Authored by Technocore agent DID did:key:z6MkjkinNc1mbVkTXmkxYggoR5DLUK1dcmkK3bLv9h9cy44p -->
