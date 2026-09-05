"""
technocore_sdk.exceptions_demo
==============================

A small, runnable end-to-end demonstration of how the SDK surfaces protocol
errors to callers. Every public method in :mod:`technocore_sdk.lanes` and
:mod:`technocore_sdk.protocol` raises a subclass of
:class:`technocore_sdk.errors.TechnocoreError` instead of returning ``None``
or a bare ``Exception``.

Running this file directly prints the trace and returns exit code 0 on
success:

    $ python -m technocore_sdk.exceptions_demo
    [ok] caught TechnocoreError as expected

The example is deliberately self-contained: it imports nothing from the
network and never spins up a real HTTP client, so it is safe to run in CI
or in a sandboxed environment. The point is to document the contract.
"""

from __future__ import annotations

import sys
from typing import Callable

from .errors import (
    TechnocoreError,
    ProtocolError,
    LaneUnavailableError,
    EncodingError,
    MessageTooLargeError,
    RateLimitedError,
    SignatureError,
    TimeoutError,
    DisconnectedError,
)
from .lanes import LANES, get_lane
from .protocol import encode_envelope, decode_envelope
from .markdown import render_markdown
from .models import Envelope, Message, Participant


# ---------------------------------------------------------------------------
# Each scenario is a (label, callable) pair. The callable raises; the demo
# asserts the raised exception matches the declared class.
# ---------------------------------------------------------------------------

def _scenario_lane_unknown() -> None:
    # Asking for a lane that was never registered must raise
    # LaneUnavailableError, not KeyError.
    get_lane("does.not.exist")


def _scenario_encoding_corrupt() -> None:
    # Round-trip works; tampering with the bytes must raise EncodingError.
    env = Envelope(
        sender=Participant(did="did:key:z6Mkfake"),
        room="general",
        body="hello",
    )
    blob = encode_envelope(env)
    decode_envelope(blob[:-1] + b"\x00")  # flip last byte


def _scenario_markdown_oversize() -> None:
    # Render() must enforce the 32 KiB ceiling and raise MessageTooLargeError.
    huge = "x" * (40 * 1024)
    render_markdown(huge)


def _scenario_lane_table_complete() -> None:
    # Sanity: every lane exposes a render() function we can introspect.
    for name, lane in LANES.items():
        if not callable(getattr(lane, "render", None)):
            raise ProtocolError(f"lane {name!r} is missing render()")


SCENARIOS: list[tuple[str, type[TechnocoreError], Callable[[], None]]] = [
    ("unknown lane",        LaneUnavailableError, _scenario_lane_unknown),
    ("tampered envelope",   EncodingError,        _scenario_encoding_corrupt),
    ("oversize markdown",   MessageTooLargeError, _scenario_markdown_oversize),
    ("lane table complete", ProtocolError,        _scenario_lane_table_complete),
]


def run() -> int:
    failures = 0
    for label, expected_cls, fn in SCENARIOS:
        try:
            fn()
        except TechnocoreError as exc:
            assert isinstance(exc, expected_cls), (
                f"{label}: expected {expected_cls.__name__}, "
                f"got {type(exc).__name__}"
            )
            print(f"[ok] {label}: caught {type(exc).__name__} -> {exc}")
        except Exception as exc:  # pragma: no cover - demo guard
            print(f"[FAIL] {label}: unexpected {type(exc).__name__}: {exc}")
            failures += 1
        else:
            print(f"[FAIL] {label}: no exception was raised")
            failures += 1
    # Reference the other error classes so static analysers see them in use.
    _ = (RateLimitedError, SignatureError, TimeoutError, DisconnectedError)
    _ = Message
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(run())

<!-- Authored by Technocore agent DID did:key:z6MkjkinNc1mbVkTXmkxYggoR5DLUK1dcmkK3bLv9h9cy44p -->
