"""Tests for wa2md.converter."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from wa2md.parser import Message
from wa2md.converter import convert


def _msg(day: int, hour: int, minute: int, sender: str | None, content: str, media_filename: str | None = None) -> Message:
    return Message(
        timestamp=datetime(2020, 1, day, hour, minute),
        sender=sender,
        content=content,
        media_filename=media_filename,
    )


# ---------------------------------------------------------------------------
# Title
# ---------------------------------------------------------------------------

class TestTitle:
    def test_default_title(self):
        md = convert([])
        assert md.startswith("# Chat: WhatsApp Chat")

    def test_custom_title(self):
        md = convert([], chat_name="My Group")
        assert "# Chat: My Group" in md


# ---------------------------------------------------------------------------
# Basic message formatting
# ---------------------------------------------------------------------------

class TestMessageFormatting:
    def test_sender_and_time(self):
        msgs = [_msg(1, 10, 30, "Alice", "Hello")]
        md = convert(msgs)
        assert "**10:30 - Alice**" in md
        assert "Hello" in md

    def test_sender_colon_content(self):
        msgs = [_msg(1, 9, 5, "Bob", "Hey there")]
        md = convert(msgs)
        assert "**09:05 - Bob**: Hey there" in md

    def test_zero_padded_time(self):
        msgs = [_msg(1, 9, 5, "Alice", "early")]
        md = convert(msgs)
        assert "09:05" in md


# ---------------------------------------------------------------------------
# Date grouping
# ---------------------------------------------------------------------------

class TestDateGrouping:
    def test_single_date_heading(self):
        msgs = [_msg(1, 10, 0, "Alice", "a"), _msg(1, 11, 0, "Bob", "b")]
        md = convert(msgs)
        assert md.count("## ") == 1

    def test_two_date_headings(self):
        msgs = [_msg(1, 10, 0, "Alice", "day1"), _msg(2, 10, 0, "Bob", "day2")]
        md = convert(msgs)
        assert md.count("## ") == 2

    def test_date_heading_format(self):
        msgs = [_msg(1, 10, 0, "Alice", "hello")]
        md = convert(msgs)
        assert "## Wednesday, 01 January 2020" in md


# ---------------------------------------------------------------------------
# System messages
# ---------------------------------------------------------------------------

class TestSystemMessages:
    def test_italic_format(self):
        msgs = [_msg(1, 9, 0, None, "Messages are encrypted.")]
        md = convert(msgs)
        assert "*Messages are encrypted.*" in md

    def test_no_sender_prefix(self):
        msgs = [_msg(1, 9, 0, None, "Alice joined")]
        md = convert(msgs)
        assert "**" not in md.split("## ")[1]  # no bold in message part after heading


# ---------------------------------------------------------------------------
# Media embedding
# ---------------------------------------------------------------------------

def _make_media(filename: str, media_type: str, path: Path | None) -> MagicMock:
    media = MagicMock()
    file_map = {filename: path} if path is not None else {}
    media.get_file_map.return_value = file_map
    media.classify.return_value = media_type
    return media


class TestMediaEmbedding:
    def test_image_embed(self, tmp_path):
        img = tmp_path / "photo.jpg"
        img.touch()
        media = _make_media("photo.jpg", "image", img)
        msgs = [_msg(1, 10, 0, "Alice", "photo.jpg (file attached)", media_filename="photo.jpg")]
        md = convert(msgs, media=media)
        assert f"![photo.jpg]({img})" in md

    def test_video_link(self, tmp_path):
        vid = tmp_path / "clip.mp4"
        vid.touch()
        media = _make_media("clip.mp4", "video", vid)
        msgs = [_msg(1, 10, 0, "Alice", "clip.mp4 (file attached)", media_filename="clip.mp4")]
        md = convert(msgs, media=media)
        assert f"[📹 clip.mp4]({vid})" in md

    def test_audio_link(self, tmp_path):
        aud = tmp_path / "voice.opus"
        aud.touch()
        media = _make_media("voice.opus", "audio", aud)
        msgs = [_msg(1, 10, 0, "Alice", "voice.opus (file attached)", media_filename="voice.opus")]
        md = convert(msgs, media=media)
        assert f"[🔊 voice.opus]({aud})" in md

    def test_unknown_link(self, tmp_path):
        doc = tmp_path / "doc.pdf"
        doc.touch()
        media = _make_media("doc.pdf", "unknown", doc)
        msgs = [_msg(1, 10, 0, "Alice", "doc.pdf (file attached)", media_filename="doc.pdf")]
        md = convert(msgs, media=media)
        assert f"[📎 doc.pdf]({doc})" in md


# ---------------------------------------------------------------------------
# Missing media / None handler
# ---------------------------------------------------------------------------

class TestMissingMedia:
    def test_none_media_handler(self):
        msgs = [_msg(1, 10, 0, "Alice", "photo.jpg (file attached)", media_filename="photo.jpg")]
        md = convert(msgs, media=None)
        assert "[📎 photo.jpg - not found]" in md

    def test_file_not_in_map(self):
        media = MagicMock()
        media.get_file_map.return_value = {}
        media.classify.return_value = "image"
        msgs = [_msg(1, 10, 0, "Alice", "missing.jpg (file attached)", media_filename="missing.jpg")]
        md = convert(msgs, media=media)
        assert "[📎 missing.jpg - not found]" in md

    def test_plain_text_no_media(self):
        msgs = [_msg(1, 10, 0, "Alice", "Just text")]
        md = convert(msgs, media=None)
        assert "Just text" in md
        assert "not found" not in md
