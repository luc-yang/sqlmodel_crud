"""Terminal output helpers."""

from __future__ import annotations

import locale
import sys
from typing import Literal, Optional, TextIO

StatusKind = Literal["success", "error", "warning", "info"]

_UNICODE_PREFIXES: dict[StatusKind, str] = {
    "success": "✓",
    "error": "✗",
    "warning": "⚠",
    "info": "ℹ",
}

_ASCII_PREFIXES: dict[StatusKind, str] = {
    "success": "[OK]",
    "error": "[ERR]",
    "warning": "[WARN]",
    "info": "[INFO]",
}


def _normalize_encoding(encoding: Optional[str]) -> str:
    if not encoding:
        return ""
    return encoding.strip().lower()


def supports_unicode_output(stream: Optional[TextIO] = None) -> bool:
    """Check whether status symbols can be safely printed."""
    target_stream = stream if stream is not None else sys.stdout
    encoding = _normalize_encoding(getattr(target_stream, "encoding", None))

    if not encoding:
        encoding = _normalize_encoding(locale.getpreferredencoding(False))

    return encoding.startswith("utf-") or encoding == "cp65001"


def status_prefix(kind: StatusKind, stream: Optional[TextIO] = None) -> str:
    """Get a status prefix for the current terminal encoding."""
    if kind not in _UNICODE_PREFIXES:
        raise ValueError(f"Unsupported status kind: {kind}")

    mapping = _UNICODE_PREFIXES if supports_unicode_output(stream) else _ASCII_PREFIXES
    return mapping[kind]
