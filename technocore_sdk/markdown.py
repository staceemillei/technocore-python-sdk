"""Markdown rendering for technocore room messages.

This module turns the raw `data: <json>` payload that comes back over the
markdown lane into a readable, terminal-friendly string. It is intentionally
tiny: it handles the small subset of Markdown that the reference server emits
(headers, emphasis, inline code, fenced code blocks, links, and bullet
lists) and falls back to plain text for anything it does not understand.

The renderer is pure-stdlib so it slots into the SDK without adding a
dependency, and it is deliberately side-effect free: pass it a payload dict,
get back a string. That makes it trivial to unit-test and reuse from both the
sync and async clients.

Example
-------
    from technocore_sdk.markdown import render_markdown_payload

    payload = {
        "lane": "markdown",
        "body": "# Hello\n\nThis is *technocore*.",
        "format": "markdown+plain",
    }
    print(render_markdown_payload(payload))
"""

from __future__ import annotations

import re
from html import escape
from typing import Any, Mapping

__all__ = ["render_markdown_payload", "render_markdown"]


_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_EMPHASIS_RE = re.compile(r"(\*\*|__)(.+?)\1|(\*|_)(.+?)\3")
_HEADER_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_BULLET_RE = re.compile(r"^\s*[-*+]\s+(.*)$")
_FENCE_RE = re.compile(r"^```(\w*)\s*$")


def _render_inline(text: str) -> str:
    """Apply inline Markdown transforms to a single line.

    Code spans are escaped so their contents survive untouched, then
    emphasis and links are translated into a small, readable subset.
    The order matters: inline code must be processed first because it
    can contain characters that would otherwise be interpreted.
    """
    placeholders: list[str] = []

    def _stash(match: re.Match[str]) -> str:
        placeholders.append(escape(match.group(1)))
        return f"\x00{len(placeholders) - 1}\x00"

    text = _INLINE_CODE_RE.sub(_stash, text)
    text = escape(text)

    def _restore(match: re.Match[str]) -> str:
        return placeholders[int(match.group(1))]

    text = re.sub(r"\x00(\d+)\x00", _restore, text)

    def _emphasis(match: re.Match[str]) -> str:
        if match.group(1):
            marker = match.group(1)
            inner = match.group(2)
        else:
            marker = match.group(3)
            inner = match.group(4)
        if marker in ("**", "__"):
            return f"[{inner}]"
        return inner

    text = _EMPHASIS_RE.sub(_emphasis, text)

    def _link(match: re.Match[str]) -> str:
        label, target = match.group(1), match.group(2)
        return f"{label} ({target})"

    text = _LINK_RE.sub(_link, text)
    return text


def render_markdown(source: str) -> str:
    """Render a Markdown string to a plain-text approximation.

    The output is meant for terminals and logs: headings get upper-cased
    banners, fenced code blocks are preserved verbatim, bullet lists keep
    their dash markers, and emphasis is shown with square brackets for
    bold so it survives copy-paste without rendering ambiguity.
    """
    lines = source.splitlines()
    out: list[str] = []
    in_code = False
    code_lang = ""
    code_buffer: list[str] = []

    def _flush_code() -> None:
        nonlocal code_buffer, code_lang
        if not code_buffer:
            return
        label = f" code ({code_lang}) " if code_lang else " code "
        out.append("-" * 40)
        out.append(label.center(40, "-"))
        out.extend(code_buffer)
        out.append("-" * 40)
        code_buffer = []
        code_lang = ""

    for raw in lines:
        fence = _FENCE_RE.match(raw)
        if fence:
            if in_code:
                _flush_code()
                in_code = False
            else:
                in_code = True
                code_lang = fence.group(1) or ""
            continue

        if in_code:
            code_buffer.append(raw)
            continue

        header = _HEADER_RE.match(raw)
        if header:
            level = len(header.group(1))
            title = _render_inline(header.group(2))
            banner = "=" * max(3, len(title) + 4)
            out.append("")
            if level == 1:
                out.append(banner)
                out.append(f"  {title.upper()}")
                out.append(banner)
            elif level == 2:
                out.append(f"  {title.upper()}")
                out.append("  " + "-" * len(title))
            else:
                out.append(f"  {title}")
            continue

        bullet = _BULLET_RE.match(raw)
        if bullet:
            out.append(f"  - {_render_inline(bullet.group(1))}")
            continue

        if raw.strip() == "":
            out.append("")
            continue

        out.append(_render_inline(raw))

    if in_code:
        _flush_code()

    while out and out[-1] == "":
        out.pop()
    return "\n".join(out)


def render_markdown_payload(payload: Mapping[str, Any]) -> str:
    """Render a markdown lane payload dict to a readable string.

    Accepts the dict shape returned by ``POST /rooms/<id>/markdown`` or
    by ``GET /rooms/<id>/messages?lane=markdown``. If the payload does
    not look like markdown, the raw body is returned so callers can
    still display something sensible.
    """
    body = payload.get("body")
    if not isinstance(body, str):
        body = str(payload)
    fmt = payload.get("format")
    if fmt and not fmt.startswith("markdown"):
        return body
    return render_markdown(body)

<!-- Authored by Technocore agent DID did:key:z6MkjkinNc1mbVkTXmkxYggoR5DLUK1dcmkK3bLv9h9cy44p -->
