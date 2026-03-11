"""Parse WhatsApp chat export text files into structured message objects.

Supports both the Android and iOS export formats, including multi-line
messages and media attachment references.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

# ---------------------------------------------------------------------------
# Regex patterns for timestamp / sender detection
# ---------------------------------------------------------------------------

# Android: "08/02/2023, 14:30 - Sender: text"
#          "8/2/23, 2:30 PM - Sender: text"
_ANDROID_MSG = re.compile(
    r"^(\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4},\s\d{1,2}:\d{2}(?::\d{2})?(?:\s[AP]M)?)"
    r"\s-\s(.+?):\s(.*)$"
)

# Android system message (no colon-separated sender)
_ANDROID_SYS = re.compile(
    r"^(\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4},\s\d{1,2}:\d{2}(?::\d{2})?(?:\s[AP]M)?)"
    r"\s-\s(.+)$"
)

# iOS: "[08/02/2023, 14:30:15] Sender: text"
#      "[2/8/23, 2:30:15 PM] Sender: text"
_IOS_MSG = re.compile(
    r"^\[(\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4},\s\d{1,2}:\d{2}(?::\d{2})?(?:\s[AP]M)?)\]"
    r"\s(.+?):\s(.*)$"
)

# iOS system message
_IOS_SYS = re.compile(
    r"^\[(\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4},\s\d{1,2}:\d{2}(?::\d{2})?(?:\s[AP]M)?)\]"
    r"\s(.+)$"
)

# ---------------------------------------------------------------------------
# Media detection patterns
# ---------------------------------------------------------------------------

# "<attached: filename.jpg>" (some Android versions)
_ATTACHED_BRACKET = re.compile(r"^<attached:\s*(.+?)>$", re.IGNORECASE)

# "filename.jpg (file attached)"
_ATTACHED_SUFFIX = re.compile(r"^(.+?)\s\(file attached\)$", re.IGNORECASE)

# "<Media omitted>" or "image omitted" / "video omitted" etc.
_OMITTED = re.compile(
    r"^(?:<Media omitted>|‎?(image|video|audio|GIF|sticker|document)\s+omitted)$",
    re.IGNORECASE,
)

# Known media file extensions
IMAGE_EXTENSIONS: frozenset[str] = frozenset(
    {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".heif", ".bmp", ".tiff", ".tif"}
)
VIDEO_EXTENSIONS: frozenset[str] = frozenset(
    {".mp4", ".mov", ".avi", ".mkv", ".3gp", ".webm", ".m4v"}
)
AUDIO_EXTENSIONS: frozenset[str] = frozenset(
    {".opus", ".ogg", ".mp3", ".m4a", ".aac", ".wav", ".flac"}
)

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class Message:
    """A single parsed WhatsApp message."""

    raw_timestamp: str
    timestamp: Optional[datetime]
    sender: Optional[str]
    content: str
    is_system: bool = False
    media_filename: Optional[str] = None
    media_type: Optional[str] = None  # "image" | "video" | "audio" | "document"


# ---------------------------------------------------------------------------
# Timestamp parsing
# ---------------------------------------------------------------------------

_DATE_FORMATS: List[str] = [
    "%d/%m/%Y, %H:%M:%S",
    "%d/%m/%Y, %H:%M",
    "%d/%m/%y, %H:%M:%S",
    "%d/%m/%y, %H:%M",
    "%m/%d/%Y, %H:%M:%S",
    "%m/%d/%Y, %H:%M",
    "%m/%d/%y, %H:%M:%S",
    "%m/%d/%y, %H:%M",
    "%d/%m/%Y, %I:%M:%S %p",
    "%d/%m/%Y, %I:%M %p",
    "%d/%m/%y, %I:%M:%S %p",
    "%d/%m/%y, %I:%M %p",
    "%m/%d/%Y, %I:%M:%S %p",
    "%m/%d/%Y, %I:%M %p",
    "%m/%d/%y, %I:%M:%S %p",
    "%m/%d/%y, %I:%M %p",
    # Dot-separated date variants (German etc.)
    "%d.%m.%Y, %H:%M:%S",
    "%d.%m.%Y, %H:%M",
    "%d.%m.%y, %H:%M:%S",
    "%d.%m.%y, %H:%M",
]


def _parse_timestamp(raw: str) -> Optional[datetime]:
    """Try to parse *raw* timestamp string using known WhatsApp formats."""
    # Normalise non-breaking and zero-width spaces
    raw = raw.replace("\u202f", " ").replace("\u200e", "").strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# Media type detection
# ---------------------------------------------------------------------------


def _media_type_from_filename(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in VIDEO_EXTENSIONS:
        return "video"
    if ext in AUDIO_EXTENSIONS:
        return "audio"
    return "document"


def _detect_media(content: str):
    """Return *(media_filename, media_type)* or *(None, None)*."""
    # Strip zero-width / left-to-right marks that WhatsApp sometimes prepends
    cleaned = content.lstrip("\u200e\u200f\u202a\u202c\u2068\u2069").strip()

    m = _ATTACHED_BRACKET.match(cleaned)
    if m:
        fname = m.group(1).strip()
        return fname, _media_type_from_filename(fname)

    m = _ATTACHED_SUFFIX.match(cleaned)
    if m:
        fname = m.group(1).strip()
        return fname, _media_type_from_filename(fname)

    omitted_match = _OMITTED.match(cleaned)
    if omitted_match:
        # No filename available – flag as omitted media
        hint = omitted_match.group(1) if omitted_match.lastindex else None
        if hint:
            if hint.lower() in ("image", "gif", "sticker"):
                return None, "image"
            if hint.lower() == "video":
                return None, "video"
            if hint.lower() == "audio":
                return None, "audio"
        return None, "document"

    return None, None


# ---------------------------------------------------------------------------
# Line classification
# ---------------------------------------------------------------------------


def _try_parse_line(line: str):
    """Return *(raw_ts, sender, content, is_system)* or *None* if not a message start."""
    # Strip byte-order mark and common invisible characters at start of file/line
    line = line.lstrip("\ufeff\u200e\u200f")

    for pattern, is_system_group in (
        (_IOS_MSG, False),
        (_ANDROID_MSG, False),
        (_IOS_SYS, True),
        (_ANDROID_SYS, True),
    ):
        m = pattern.match(line)
        if m:
            raw_ts = m.group(1)
            if is_system_group:
                return raw_ts, None, m.group(2), True
            return raw_ts, m.group(2), m.group(3), False
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_chat(text: str) -> List[Message]:
    """Parse *text* (the contents of a WhatsApp _chat.txt) into a list of
    :class:`Message` objects.

    Multi-line messages are handled by accumulating continuation lines until
    the next timestamped message is encountered.
    """
    messages: List[Message] = []
    current: Optional[dict] = None

    for raw_line in text.splitlines():
        parsed = _try_parse_line(raw_line)
        if parsed is not None:
            # Flush previous message
            if current is not None:
                messages.append(_build_message(current))
            raw_ts, sender, content, is_system = parsed
            current = {
                "raw_ts": raw_ts,
                "sender": sender,
                "lines": [content],
                "is_system": is_system,
            }
        else:
            # Continuation line of the current message
            if current is not None:
                current["lines"].append(raw_line)
            # Lines before any message (e.g. export header) are silently ignored

    if current is not None:
        messages.append(_build_message(current))

    return messages


def _build_message(current: dict) -> Message:
    raw_ts: str = current["raw_ts"]
    sender: Optional[str] = current["sender"]
    is_system: bool = current["is_system"]
    content = "\n".join(current["lines"])

    timestamp = _parse_timestamp(raw_ts)
    media_filename, media_type = _detect_media(content)

    return Message(
        raw_timestamp=raw_ts,
        timestamp=timestamp,
        sender=sender,
        content=content,
        is_system=is_system,
        media_filename=media_filename,
        media_type=media_type,
    )
