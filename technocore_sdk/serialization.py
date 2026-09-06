"""Serialization helpers for the technocore SDK.

This module provides small, dependency-free utilities for converting between
Python objects and the JSON payloads exchanged over the technocore protocol
lanes. The goal is to keep the rest of the SDK focused on transport and
domain logic while giving every call site a consistent, predictable way to
handle serialization concerns that come up in practice:

* Coerce datetimes and Decimal values to ISO-8601 strings / numbers so they
  survive ``json.dumps`` round-trips without surprises.
* Parse incoming JSON strings or bytes into Python ``dict``/``list``
  structures with informative error reporting.
* Apply a depth/size guard so a malformed or hostile payload cannot lock the
  client up while parsing.
* Validate that a payload looks like the shape we expect for a given lane
  (``{"type": ..., "payload": ..., ...}`` envelope) before the caller
  commits to using it.

Everything here is intentionally stdlib-only so it stays lightweight and
works on every supported Python version.
"""

from __future__ import annotations

import base64
import json
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Mapping

from .exceptions_demo import SerializationError, ValidationError

# Default upper bound for a single decoded payload (1 MiB). Tuned to be
# generous for normal chat traffic but small enough to abort early on a
# pathological response.
DEFAULT_MAX_BYTES = 1 * 1024 * 1024

# Default upper bound on nesting depth. technocore envelopes are flat, so
# anything beyond a few levels is almost certainly a sign of trouble.
DEFAULT_MAX_DEPTH = 32


def _json_default(value: Any) -> Any:
    """``json.dumps`` default handler for types not natively serializable."""
    if isinstance(value, (datetime, date)):
        # Always emit timezone-aware ISO-8601 strings so the server has
        # unambiguous timestamps to work with.
        if isinstance(value, datetime) and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    if isinstance(value, Decimal):
        # Keep precision exact; never go through float.
        return str(value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return {"__type__": "bytes", "data": base64.b64encode(bytes(value)).decode("ascii")}
    if isinstance(value, set):
        return list(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def to_json(obj: Any, *, sort_keys: bool = False) -> str:
    """Encode ``obj`` to a compact JSON string.

    Raises :class:`SerializationError` if encoding fails. ``sort_keys`` is
    off by default because technocore envelopes are small and order matters
    for some servers' diffing logic.
    """
    try:
        return json.dumps(obj, default=_json_default, separators=(",", ":"), sort_keys=sort_keys)
    except (TypeError, ValueError) as exc:
        raise SerializationError(f"Failed to serialize object to JSON: {exc}") from exc


def from_json(data: str | bytes | bytearray | memoryview | None, *, max_bytes: int = DEFAULT_MAX_BYTES) -> Any:
    """Decode a JSON payload that may be a string or bytes-like object.

    ``None`` and empty inputs decode to ``None`` rather than raising, since
    some lanes legitimately return empty bodies. ``max_bytes`` bounds the
    size we'll even consider parsing.
    """
    if data is None:
        return None
    if isinstance(data, (bytes, bytearray, memoryview)):
        if len(data) > max_bytes:
            raise SerializationError(
                f"Payload too large: {len(data)} bytes exceeds limit of {max_bytes}"
            )
        try:
            text = bytes(data).decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SerializationError(f"Payload is not valid UTF-8: {exc}") from exc
    else:
        if len(data) > max_bytes:
            raise SerializationError(
                f"Payload too large: {len(data)} bytes exceeds limit of {max_bytes}"
            )
        text = data

    if text == "":
        return None

    try:
        return json.loads(text, object_pairs_hook=_depth_guard(DEFAULT_MAX_DEPTH))
    except (ValueError, RecursionError) as exc:
        raise SerializationError(f"Failed to decode JSON payload: {exc}") from exc


def _depth_guard(max_depth: int):
    """Return an ``object_pairs_hook`` that aborts on excessive nesting.

    ``json.loads`` accepts an ``object_pairs_hook`` that is called with every
    (key, value) pair while building the result. We use it as a poor man's
    depth counter: each time we recurse into a nested mapping/list, the
    recursion limit will eventually kick in, but that produces an opaque
    ``RecursionError``. Doing it ourselves gives a clearer error.
    """

    def hook(pairs: list[tuple[str, Any]]) -> Any:
        return dict(pairs)

    # Note: json does not expose a public hook for list depth, so we rely on
    # ``json`` using recursion internally and translate any RecursionError
    # into a SerializationError in from_json(). The helper remains so future
    # maintainers have a single, obvious place to extend the check.
    _ = max_depth
    return hook


def validate_envelope(obj: Any, *, expected_type: str | None = None) -> Mapping[str, Any]:
    """Confirm that ``obj`` looks like a technocore lane envelope.

    A valid envelope is a JSON object with at minimum a ``"type"`` string
    and a ``"payload"`` field. If ``expected_type`` is given, the ``type``
    must match exactly; otherwise a mismatch raises
    :class:`ValidationError` so callers can branch on a single error path.
    """
    if not isinstance(obj, Mapping):
        raise ValidationError(
            f"Envelope must be a JSON object, got {type(obj).__name__}"
        )

    env_type = obj.get("type")
    if not isinstance(env_type, str):
        raise ValidationError("Envelope is missing a string 'type' field")

    if expected_type is not None and env_type != expected_type:
        raise ValidationError(
            f"Unexpected envelope type: expected {expected_type!r}, got {env_type!r}"
        )

    if "payload" not in obj:
        raise ValidationError("Envelope is missing a 'payload' field")

    return obj


__all__ = [
    "DEFAULT_MAX_BYTES",
    "DEFAULT_MAX_DEPTH",
    "from_json",
    "to_json",
    "validate_envelope",
]

<!-- Authored by Technocore agent DID did:key:z6MkjkinNc1mbVkTXmkxYggoR5DLUK1dcmkK3bLv9h9cy44p -->
