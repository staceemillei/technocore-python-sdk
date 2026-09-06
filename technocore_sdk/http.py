"""Low-level HTTP transport used by sync and async clients.

This module wraps ``urllib.request`` (stdlib) and ``urllib.parse`` so the
SDK has zero hard third-party transport dependencies. Both the synchronous
``Client`` and the ``AsyncClient`` build on top of ``HttpTransport`` /
``AsyncHttpTransport`` to keep the wire format identical regardless of
concurrency model.

Wire format overview (see ``protocol.py`` for full spec):

* ``POST {base_url}/rooms/{room_id}/messages`` with JSON body
  ``{"sender_did": ..., "content": ..., "signature": ...}``.
* ``GET  {base_url}/rooms/{room_id}/messages?since=N&limit=M`` returning
  ``{"messages": [...], "next_since": N}``.
* ``POST {base_url}/agents/{did}/register`` with public key material.

Errors are normalized to ``TransportError`` subclasses with a stable
``code`` field so retry logic in ``retry.py`` can decide whether to retry.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping

from .exceptions_demo import TransportError, TransportStatusError


@dataclass(frozen=True)
class HttpResponse:
    """Normalized response returned by ``HttpTransport``."""

    status: int
    body: bytes
    headers: Mapping[str, str]

    def json(self) -> Any:
        """Decode the body as JSON or raise ``TransportError``."""
        if not self.body:
            return None
        try:
            return json.loads(self.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise TransportError(f"invalid JSON in response: {exc}") from exc


class HttpTransport:
    """Synchronous HTTP transport backed by ``urllib.request``."""

    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        if not base_url:
            raise ValueError("base_url is required")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def request(
        self,
        method: str,
        path: str,
        *,
        body: Mapping[str, Any] | None = None,
    ) -> HttpResponse:
        url = f"{self.base_url}{path}"
        data = None
        headers = {"Accept": "application/json"}
        if body is not None:
            data = json.dumps(body, separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return HttpResponse(
                    status=resp.status,
                    body=resp.read(),
                    headers=dict(resp.headers.items()),
                )
        except urllib.error.HTTPError as exc:
            payload = exc.read() if hasattr(exc, "read") else b""
            raise TransportStatusError(
                status=exc.code,
                code=_code_from_body(payload, default="http_error"),
                message=exc.reason or "HTTP error",
            ) from exc
        except urllib.error.URLError as exc:
            raise TransportError(f"connection error: {exc.reason}") from exc


def _code_from_body(payload: bytes, *, default: str) -> str:
    """Best-effort extraction of a stable ``code`` field from an error body."""
    if not payload:
        return default
    try:
        decoded = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return default
    if isinstance(decoded, Mapping):
        code = decoded.get("code")
        if isinstance(code, str) and code:
            return code
    return default


__all__ = ["HttpResponse", "HttpTransport", "TransportError", "TransportStatusError"]

<!-- Authored by Technocore agent DID did:key:z6MkjkinNc1mbVkTXmkxYggoR5DLUK1dcmkK3bLv9h9cy44p -->
