"""Lightweight PII redaction applied before any customer text reaches the LLM API.

Regex-based, not exhaustive — covers the two most common patterns (email,
phone). Applied only to text sent to the API; local operations (BM25
retrieval, quote-grounding checks against the original ticket body) use the
unredacted text, since neither leaves the process.
"""
from __future__ import annotations

import re

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"(?<!\d)(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}(?!\d)")


def redact_text(text: str) -> str:
    text = _EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    text = _PHONE_RE.sub("[REDACTED_PHONE]", text)
    return text
