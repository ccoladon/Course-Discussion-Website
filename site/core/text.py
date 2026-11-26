"""Small, shared helpers: text sanitising and code normalisation."""

from __future__ import annotations

import re

import bleach

MAX_BODY_LENGTH = 10_000


def sanitize_markdown(text: str) -> str:
    """Escape raw HTML while leaving Markdown/LaTeX syntax intact.

    The client renders Markdown + KaTeX from this source, so the server's job
    is only to neutralise HTML injection. ``strip=False`` means tags are
    escaped (``<b>`` -> ``&lt;b&gt;``) rather than silently removed.
    """
    cleaned = bleach.clean(text, tags=[], attributes={}, protocols=[], strip=False)
    return cleaned.replace("\r\n", "\n").strip()


_COURSE_CODE_RE = re.compile(r"^([A-Za-z]+)\s*[-_]?\s*(\d{1,4}[A-Za-z]*)$")


def normalize_course_code(raw: str) -> str:
    """``cs101`` / ``CS-101`` / ``Comp Sci 101`` -> ``CS 101``."""
    text = " ".join(raw.split()).upper()
    match = _COURSE_CODE_RE.match(text)
    if match:
        return f"{match.group(1)} {match.group(2)}"
    return text
