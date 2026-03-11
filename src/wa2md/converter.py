"""Convert a list of parsed :class:`~wa2md.parser.Message` objects to Markdown.

The generated Markdown:
- Groups messages by date.
- Renders each message as a blockquote with sender and timestamp.
- Embeds images and GIFs inline (``![alt](path)``).
- Embeds videos with an HTML ``<video>`` tag (wide compatibility).
- Links audio files as playable ``<audio>`` elements.
- Falls back to a plain hyperlink for unknown media types.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

from .parser import Message

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_IMAGE_EXTENSIONS = frozenset(
    {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".heif", ".bmp", ".tiff", ".tif"}
)
_VIDEO_EXTENSIONS = frozenset({".mp4", ".mov", ".avi", ".mkv", ".3gp", ".webm", ".m4v"})
_AUDIO_EXTENSIONS = frozenset({".opus", ".ogg", ".mp3", ".m4a", ".aac", ".wav", ".flac"})


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _media_tag(filename: str, rel_path: str) -> str:
    """Return the appropriate Markdown / HTML snippet for *filename*."""
    ext = Path(filename).suffix.lower()
    if ext in _IMAGE_EXTENSIONS:
        return f"![{filename}]({rel_path})"
    if ext in _VIDEO_EXTENSIONS:
        return (
            f'<video controls width="480" src="{rel_path}">'
            f'<a href="{rel_path}">{filename}</a></video>'
        )
    if ext in _AUDIO_EXTENSIONS:
        return (
            f'<audio controls src="{rel_path}">'
            f'<a href="{rel_path}">{filename}</a></audio>'
        )
    return f"[{filename}]({rel_path})"


def _format_message_body(
    message: Message,
    media_index: Dict[str, Path],
    media_rel_dir: str,
) -> str:
    """Return the Markdown body for *message*."""
    if message.media_filename and message.media_filename in media_index:
        rel_path = os.path.join(media_rel_dir, message.media_filename).replace("\\", "/")
        return _media_tag(message.media_filename, rel_path)

    if message.media_filename and message.media_filename not in media_index:
        # File referenced but not present in the media index
        return f"*[media not found: {message.media_filename}]*"

    if message.media_type and message.media_filename is None:
        # "image omitted" / "video omitted" style – no file available
        return f"*[{message.media_type} omitted]*"

    # Regular text message – preserve line breaks
    lines = message.content.splitlines()
    return "  \n".join(lines)


def _date_heading(message: Message) -> str:
    if message.timestamp:
        return message.timestamp.strftime("%A, %d %B %Y")
    return "Unknown date"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def convert(
    messages: List[Message],
    title: str = "WhatsApp Chat",
    media_index: Optional[Dict[str, Path]] = None,
    media_rel_dir: str = "media",
) -> str:
    """Convert *messages* to a Markdown string.

    Parameters
    ----------
    messages:
        Parsed :class:`~wa2md.parser.Message` objects (from
        :func:`~wa2md.parser.parse_chat`).
    title:
        The H1 heading placed at the top of the document.
    media_index:
        Mapping of ``filename → Path`` as returned by
        :func:`~wa2md.media_handler.build_media_index`.  Pass ``{}`` or
        ``None`` if no media files are available.
    media_rel_dir:
        The relative directory prefix written into image/video/audio references
        in the Markdown output.  Defaults to ``"media"``.
    """
    if media_index is None:
        media_index = {}

    lines: List[str] = [f"# {title}", ""]

    current_date: Optional[str] = None

    for msg in messages:
        # ── date separator ──────────────────────────────────────────────────
        date_str = _date_heading(msg)
        if date_str != current_date:
            current_date = date_str
            lines.append(f"## {date_str}")
            lines.append("")

        # ── system messages ─────────────────────────────────────────────────
        if msg.is_system:
            lines.append(f"*{msg.content}*")
            lines.append("")
            continue

        # ── regular message ─────────────────────────────────────────────────
        time_str = (
            msg.timestamp.strftime("%H:%M") if msg.timestamp else msg.raw_timestamp
        )
        sender = msg.sender or "Unknown"
        body = _format_message_body(msg, media_index, media_rel_dir)

        lines.append(f"**{sender}** `{time_str}`")
        lines.append("")
        lines.append(f"> {body}")
        lines.append("")

    return "\n".join(lines)
