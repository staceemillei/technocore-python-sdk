"""
technocore_sdk.validation
========================

Lightweight runtime validation helpers used across the SDK.

The protocol uses plain JSON over HTTP. Schemas evolve, and the server may
return a payload the SDK does not yet know about (forward compatibility) or,
more annoyingly, an old payload from a proxy that stripped fields. These
helpers give every typed method a uniform way to:

  * raise a precise ``ValidationError`` instead of letting ``KeyError`` /
    ``AttributeError`` surface from deep inside a model.
  * normalise payloads (``from_dict`` factories) so downstream code can rely
    on field presence.
  * attach the offending path to the error so callers can log it.

Nothing here depends on third-party libraries, which keeps the SDK small and
importable in any environment where ``httpx`` already runs.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable, Mapping, Type, TypeVar

from .exceptions_demo import ValidationError

T = TypeVar("T")

__all__ = [
    "require_keys",
    "coerce_int",
    "coerce_str",
    "coerce_bool",
    "coerce_list",
    "from_dict",
]


# --------------------------------------------------------------------------- #
# Low-level key/coercion primitives
# --------------------------------------------------------------------------- #


def require_keys(payload: Mapping[str, Any], keys: Iterable[str], *, path: str = "$") -> None:
    """Verify that ``payload`` contains every key in ``keys``.

    Missing keys raise :class:`ValidationError` whose message points at the
    JSON path of the first absent field, e.g. ``"$.room_id"``.
    """
    missing = [k for k in keys if k not in payload]
    if missing:
        first = missing[0]
        raise ValidationError(
            f"missing required field {path}.{first}",
            field=first,
            path=f"{path}.{first}",
        )


def coerce_int(value: Any, *, field: str, default: int | None = None) -> int:
    """Best-effort integer coercion used for pagination cursors / timestamps."""
    if value is None:
        if default is not None:
            return default
        raise ValidationError(f"{field} is required", field=field)
    if isinstance(value, bool):
        # bool is a subclass of int in Python; reject it explicitly because
        # almost every API treats True/False as a client bug here.
        raise ValidationError(f"{field} must be int, got bool", field=field)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value, 10)
        except ValueError as exc:
            raise ValidationError(
                f"{field}={value!r} is not an integer",
                field=field,
            ) from exc
    raise ValidationError(
        f"{field} must be int, got {type(value).__name__}", field=field
    )


def coerce_str(value: Any, *, field: str, default: str | None = None, allow_empty: bool = False) -> str:
    """Coerce a value to ``str`` with explicit handling for ``None`` / empty."""
    if value is None:
        if default is not None:
            return default
        raise ValidationError(f"{field} is required", field=field)
    if not isinstance(value, str):
        value = str(value)
    if not allow_empty and not value:
        raise ValidationError(f"{field} must be non-empty", field=field)
    return value


def coerce_bool(value: Any, *, field: str, default: bool | None = None) -> bool:
    """Coerce a value to ``bool`` accepting the usual JSON-ish truthy strings."""
    if value is None:
        if default is not None:
            return default
        raise ValidationError(f"{field} is required", field=field)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off", ""}:
            return False
    raise ValidationError(
        f"{field}={value!r} is not a boolean", field=field
    )


def coerce_list(
    value: Any,
    *,
    field: str,
    item_coercer: Callable[[Any, str], T] | None = None,
) -> list[T]:
    """Coerce ``value`` to a list, optionally mapping each item through ``item_coercer``."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        items = list(value)
    elif isinstance(value, str):
        # Permit comma separated strings because some legacy lanes send them.
        items = [part for part in value.split(",") if part != ""]
    else:
        raise ValidationError(
            f"{field} must be list, got {type(value).__name__}", field=field
        )
    if item_coercer is None:
        return items
    return [item_coercer(item, f"{field}[{idx}]") for idx, item in enumerate(items)]


# --------------------------------------------------------------------------- #
# Generic ``from_dict`` dispatcher
# --------------------------------------------------------------------------- #


def from_dict(model_cls: Type[T], payload: Any, *, path: str = "$") -> T:
    """Construct a model instance from a raw payload.

    ``model_cls`` must expose a ``model_validate`` classmethod (Pydantic v2
    style) **or** a ``from_dict`` classmethod. The first matching interface
    wins. ``None`` payloads become ``None`` for nullable fields; anything else
    is passed through.
    """
    if payload is None:
        # The caller is responsible for deciding whether None is acceptable.
        # We return None so optional fields propagate naturally.
        return None  # type: ignore[return-value]
    validate = getattr(model_cls, "model_validate", None)
    if callable(validate):
        try:
            return validate(payload)
        except Exception as exc:  # pragma: no cover - rewrapped for context
            raise ValidationError(
                f"failed to validate {model_cls.__name__} at {path}: {exc}",
                path=path,
            ) from exc
    from_dict_method = getattr(model_cls, "from_dict", None)
    if callable(from_dict_method):
        return from_dict_method(payload)
    raise ValidationError(
        f"{model_cls.__name__} has neither model_validate nor from_dict",
        path=path,
    )

<!-- Authored by Technocore agent DID did:key:z6MkjkinNc1mbVkTXmkxYggoR5DLUK1dcmkK3bLv9h9cy44p -->
