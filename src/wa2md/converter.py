"""Convert parsed WhatsApp messages to a Markdown document."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

from .parser import Message
from .media_handler import MediaHandler


def _embed_media(filename: str, path: Optional[Path], media_type: str) -> str:
    if path is None:
        return f"[📎 {filename} - not found]"
    path_str = str(path)
    if media_type == "image":
        return f"![{filename}]({path_str})"
    if media_type == "video":
        return f"[📹 {filename}]({path_str})"
    if media_type == "audio":
        return f"[🔊 {filename}]({path_str})"
    return f"[📎 {filename}]({path_str})"


def _format_message(msg: Message, media: Optional[MediaHandler]) -> str:
    time_str = msg.timestamp.strftime("%H:%M")

    if msg.sender is None:
        return f"*{msg.content}*"

    header = f"**{time_str} - {msg.sender}**"

    if msg.media_filename is not None:
        file_map = media.get_file_map() if media is not None else {}
        path = file_map.get(msg.media_filename)
        media_type = media.classify(msg.media_filename) if media is not None else "unknown"
        embedded = _embed_media(msg.media_filename, path, media_type)
        # Append any additional text content if present
        extra = msg.content
        # Strip the raw "file attached" line – it's replaced by the embed
        if "(file attached)" in extra.lower():
            extra = ""
        if extra.strip():
            return f"{header}: {extra}\n{embedded}"
        return f"{header}: {embedded}"

    return f"{header}: {msg.content}"


def convert(
    messages: list[Message],
    media: Optional[MediaHandler] = None,
    chat_name: str = "WhatsApp Chat",
) -> str:
    lines: list[str] = [f"# Chat: {chat_name}", ""]

    current_date: Optional[date] = None

    for msg in messages:
        msg_date = msg.timestamp.date()
        if msg_date != current_date:
            current_date = msg_date
            lines.append(f"## {msg_date.strftime('%A, %d %B %Y')}")
            lines.append("")

        lines.append(_format_message(msg, media))

    lines.append("")
    return "\n".join(lines)
