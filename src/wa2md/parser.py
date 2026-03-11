"""Parse WhatsApp chat export .txt files into Message objects."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class Message:
    timestamp: datetime
    sender: Optional[str]
    content: str
    media_filename: Optional[str] = field(default=None)


# ---------------------------------------------------------------------------
# Timestamp patterns
# ---------------------------------------------------------------------------

# Android 24 h:  16/01/2020, 14:23 -
# Android 12 h:  1/16/20, 2:23 PM -
_ANDROID_24H = re.compile(
    r"^(\d{1,2}/\d{1,2}/\d{2,4}),\s(\d{1,2}:\d{2})\s-\s"
)
_ANDROID_12H = re.compile(
    r"^(\d{1,2}/\d{1,2}/\d{2,4}),\s(\d{1,2}:\d{2}\s(?:AM|PM))\s-\s"
)
# iOS:           [16/01/2020, 14:23:45]
_IOS = re.compile(
    r"^\[(\d{1,2}/\d{1,2}/\d{2,4}),\s(\d{1,2}:\d{2}(?::\d{2})?(?:\s(?:AM|PM))?)\]\s"
)

# Media placeholder patterns
_MEDIA_OMITTED = re.compile(
    r"^[‎\s]*(?:<Media omitted>|image omitted|video omitted|GIF omitted|audio omitted|sticker omitted)",
    re.IGNORECASE,
)
# "IMG-20200116-WA0001.jpg (file attached)" – also handles leading LTR mark
_FILE_ATTACHED = re.compile(r"^[‎\s]*([\w.\-]+?\.\w+)\s+\(file attached\)", re.IGNORECASE)

# Sender + content split:  "Alice: Hello"
_SENDER_SPLIT = re.compile(r"^([^:]+?):\s(.*)", re.DOTALL)


def _parse_datetime_android_24h(date_str: str, time_str: str) -> datetime:
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%m/%d/%Y", "%m/%d/%y"):
        try:
            d = datetime.strptime(date_str, fmt)
            t = datetime.strptime(time_str, "%H:%M")
            return d.replace(hour=t.hour, minute=t.minute)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date={date_str!r} time={time_str!r}")


def _parse_datetime_12h(date_str: str, time_str: str) -> datetime:
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%m/%d/%Y", "%m/%d/%y"):
        try:
            d = datetime.strptime(date_str, fmt)
            t = datetime.strptime(time_str.strip(), "%I:%M %p")
            return d.replace(hour=t.hour, minute=t.minute)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date={date_str!r} time={time_str!r}")


def _parse_datetime_ios(date_str: str, time_str: str) -> datetime:
    time_str = time_str.strip()
    # Try 12 h with seconds, 12 h without, 24 h with seconds, 24 h without
    for time_fmt in ("%I:%M:%S %p", "%I:%M %p", "%H:%M:%S", "%H:%M"):
        for date_fmt in ("%d/%m/%Y", "%d/%m/%y", "%m/%d/%Y", "%m/%d/%y"):
            try:
                d = datetime.strptime(date_str, date_fmt)
                t = datetime.strptime(time_str, time_fmt)
                return d.replace(hour=t.hour, minute=t.minute, second=t.second)
            except ValueError:
                continue
    raise ValueError(f"Cannot parse date={date_str!r} time={time_str!r}")


def _extract_media(content: str) -> tuple[str, Optional[str]]:
    """Return (cleaned_content, media_filename_or_None)."""
    fa = _FILE_ATTACHED.match(content)
    if fa:
        return content, fa.group(1)
    if _MEDIA_OMITTED.match(content):
        return content, None
    return content, None


def _build_message(timestamp: datetime, raw_body: str) -> Message:
    """Split sender from body and detect media."""
    m = _SENDER_SPLIT.match(raw_body)
    if m:
        sender = m.group(1).strip()
        content = m.group(2)
        content, media_filename = _extract_media(content)
        return Message(timestamp=timestamp, sender=sender, content=content, media_filename=media_filename)
    # System message
    return Message(timestamp=timestamp, sender=None, content=raw_body.strip())


def parse_text(text: str) -> list[Message]:
    """Parse the full text of a WhatsApp chat export."""
    messages: list[Message] = []
    pending_ts: Optional[datetime] = None
    pending_body: Optional[str] = None

    for line in text.splitlines():
        ts: Optional[datetime] = None
        body: Optional[str] = None

        m = _ANDROID_12H.match(line)
        if m:
            ts = _parse_datetime_12h(m.group(1), m.group(2))
            body = line[m.end():]
        else:
            m = _ANDROID_24H.match(line)
            if m:
                ts = _parse_datetime_android_24h(m.group(1), m.group(2))
                body = line[m.end():]
            else:
                m = _IOS.match(line)
                if m:
                    ts = _parse_datetime_ios(m.group(1), m.group(2))
                    body = line[m.end():]

        if ts is not None and body is not None:
            # Flush previous
            if pending_ts is not None and pending_body is not None:
                messages.append(_build_message(pending_ts, pending_body))
            pending_ts = ts
            pending_body = body
        else:
            # Continuation line
            if pending_body is not None:
                pending_body += "\n" + line

    if pending_ts is not None and pending_body is not None:
        messages.append(_build_message(pending_ts, pending_body))

    return messages


def parse_file(path: Path) -> list[Message]:
    """Parse a WhatsApp chat export file."""
    text = path.read_text(encoding="utf-8", errors="replace")
    return parse_text(text)
