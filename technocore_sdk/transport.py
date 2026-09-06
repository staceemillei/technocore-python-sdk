"""HTTP transport layer for the technocore SDK.

This module isolates the HTTP details from the higher-level ``Client`` /
``AsyncClient`` classes. The goal is to make the rest of the SDK easy to
unit-test (by injecting a fake transport) and easy to swap if the underlying
wire format ever changes.

Design notes
------------
* The transport only knows about bytes in / bytes out and the status line.
* All retry, signing, and serialization concerns live in their own modules
  and are layered *on top of* a transport, not inside one.
* Both a sync (``SyncTransport``) and async (``AsyncTransport``) variant are
  provided so the public clients can stay thin.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Protocol
from urllib import error as urllib_error
from urllib import request as urllib_request

from .exceptions_demo import TransportError


@dataclass(frozen=True)
class HttpRequest:
    """A minimal, transport-agnostic description of an outgoing request."""

    method: str
    url: str
    headers: Mapping[str, str]
    body: bytes

    def header(self, name: str, default: Optional[str] = None) -> Optional[str]:
        # ``Mapping[str, str]`` is the declared type, but be defensive against
        # callers passing something with case-insensitive lookup.
        get = getattr(self.headers, "get", None)
        if callable(get):
            return get(name, default)
        return self.headers.get(name, default) if hasattr(self.headers, "get") else default


@dataclass(frozen=True)
class HttpResponse:
    """A minimal, transport-agnostic description of an incoming response."""

    status: int
    headers: Mapping[str, str]
    body: bytes

    def json(self) -> Any:
        if not self.body:
            return None
        try:
            return json.loads(self.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise TransportError(f"response was not valid utf-8 JSON: {exc}") from exc


class Transport(Protocol):
    """Sync transport interface. Implementations: ``SyncHttpTransport``, fakes in tests."""

    def send(self, request: HttpRequest) -> HttpResponse: ...


class AsyncTransport(Protocol):
    """Async transport interface. Implementations: ``AsyncHttpTransport``, fakes in tests."""

    async def send(self, request: HttpRequest) -> HttpResponse: ...


class SyncHttpTransport:
    """Default sync transport backed by ``urllib``.

    Kept dependency-free on purpose so the SDK stays installable in restricted
    environments. ``urllib`` is part of the standard library and has a stable
    enough surface for our needs.
    """

    def send(self, request: HttpRequest) -> HttpResponse:
        req = urllib_request.Request(
            url=request.url,
            data=request.body or None,
            method=request.method.upper(),
            headers=dict(request.headers),
        )
        try:
            with urllib_request.urlopen(req) as resp:  # nosec - caller controls URL
                body = resp.read()
                return HttpResponse(
                    status=resp.status,
                    headers=dict(resp.headers.items()),
                    body=body,
                )
        except urllib_error.HTTPError as exc:
            # ``HTTPError`` doubles as a response, which is convenient.
            body = exc.read() if hasattr(exc, "read") else b""
            return HttpResponse(status=exc.code, headers=dict(exc.headers.items()), body=body)
        except urllib_error.URLError as exc:
            raise TransportError(f"network error contacting {request.url}: {exc.reason}") from exc


class AsyncHttpTransport:
    """Default async transport.

    The SDK does not want to hard-pin an HTTP library, so this implementation
    uses ``asyncio``'s default thread-pool bridge. Production users are
    encouraged to pass a faster transport (e.g. ``httpx.AsyncClient``) into
    ``AsyncClient(transport=...)""" once they import those libraries
    themselves.
    """

    def __init__(self) -> None:
        import asyncio  # local import keeps top-level deps minimal

        self._asyncio = asyncio

    async def send(self, request: HttpRequest) -> HttpResponse:
        loop = self._asyncio.get_running_loop()
        sync = SyncHttpTransport()
        return await loop.run_in_executor(None, sync.send, request)


__all__ = [
    "HttpRequest",
    "HttpResponse",
    "Transport",
    "AsyncTransport",
    "SyncHttpTransport",
    "AsyncHttpTransport",
]

<!-- Authored by Technocore agent DID did:key:z6MkjkinNc1mbVkTXmkxYggoR5DLUK1dcmkK3bLv9h9cy44p -->
