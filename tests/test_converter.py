"""Unit tests for wa2md.converter."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from wa2md.converter import _media_tag, convert
from wa2md.parser import Message


# ---------------------------------------------------------------------------
# _media_tag
# ---------------------------------------------------------------------------


class TestMediaTag:
    def test_jpeg_renders_as_image(self):
        tag = _media_tag("photo.jpg", "media/photo.jpg")
        assert tag == "![photo.jpg](media/photo.jpg)"

    def test_gif_renders_as_image(self):
        tag = _media_tag("anim.gif", "media/anim.gif")
        assert tag.startswith("![")

    def test_mp4_renders_as_video(self):
        tag = _media_tag("clip.mp4", "media/clip.mp4")
        assert "<video" in tag
        assert "media/clip.mp4" in tag

    def test_opus_renders_as_audio(self):
        tag = _media_tag("voice.opus", "media/voice.opus")
        assert "<audio" in tag
        assert "media/voice.opus" in tag

    def test_pdf_renders_as_link(self):
        tag = _media_tag("doc.pdf", "media/doc.pdf")
        assert tag == "[doc.pdf](media/doc.pdf)"

    def test_webm_renders_as_video(self):
        tag = _media_tag("clip.webm", "media/clip.webm")
        assert "<video" in tag


# ---------------------------------------------------------------------------
# convert – basic structure
# ---------------------------------------------------------------------------


def _make_msg(sender, content, ts=None, is_system=False, media_filename=None, media_type=None):
    if ts is None:
        ts = datetime(2023, 2, 8, 14, 30)
    return Message(
        raw_timestamp="08/02/2023, 14:30",
        timestamp=ts,
        sender=sender,
        content=content,
        is_system=is_system,
        media_filename=media_filename,
        media_type=media_type,
    )


class TestConvertBasic:
    def test_title_heading(self):
        md = convert([], title="My Chat")
        assert md.startswith("# My Chat")

    def test_empty_messages(self):
        md = convert([])
        assert "# WhatsApp Chat" in md

    def test_date_group_heading(self):
        msgs = [_make_msg("Alice", "Hello")]
        md = convert(msgs)
        assert "## Wednesday, 08 February 2023" in md

    def test_sender_in_output(self):
        msgs = [_make_msg("Alice", "Hello")]
        md = convert(msgs)
        assert "**Alice**" in md

    def test_content_in_output(self):
        msgs = [_make_msg("Alice", "Hello there")]
        md = convert(msgs)
        assert "Hello there" in md

    def test_time_displayed(self):
        msgs = [_make_msg("Alice", "Hello", ts=datetime(2023, 2, 8, 9, 5))]
        md = convert(msgs)
        assert "`09:05`" in md

    def test_system_message_italicised(self):
        msgs = [_make_msg(None, "Alice joined via link", is_system=True)]
        md = convert(msgs)
        assert "*Alice joined via link*" in md
        assert "**None**" not in md


class TestConvertMedia:
    def test_image_embedded_when_in_index(self, tmp_path):
        img = tmp_path / "IMG-001.jpg"
        img.write_bytes(b"fake-jpeg")
        media_index = {"IMG-001.jpg": img}
        msgs = [_make_msg("Alice", "IMG-001.jpg (file attached)", media_filename="IMG-001.jpg", media_type="image")]
        md = convert(msgs, media_index=media_index, media_rel_dir="media")
        assert "![IMG-001.jpg](media/IMG-001.jpg)" in md

    def test_missing_media_shows_not_found(self):
        msgs = [_make_msg("Alice", "IMG-001.jpg (file attached)", media_filename="IMG-001.jpg", media_type="image")]
        md = convert(msgs, media_index={})
        assert "media not found" in md

    def test_omitted_media_shows_omitted(self):
        msgs = [_make_msg("Alice", "image omitted", media_filename=None, media_type="image")]
        md = convert(msgs, media_index={})
        assert "image omitted" in md

    def test_video_html_tag(self, tmp_path):
        vid = tmp_path / "VID-001.mp4"
        vid.write_bytes(b"fake-mp4")
        media_index = {"VID-001.mp4": vid}
        msgs = [_make_msg("Bob", "VID-001.mp4 (file attached)", media_filename="VID-001.mp4", media_type="video")]
        md = convert(msgs, media_index=media_index, media_rel_dir="media")
        assert "<video" in md
        assert "media/VID-001.mp4" in md

    def test_gif_embedded_as_image(self, tmp_path):
        gif = tmp_path / "GIF-001.gif"
        gif.write_bytes(b"GIF89a")
        media_index = {"GIF-001.gif": gif}
        msgs = [_make_msg("Alice", "GIF-001.gif (file attached)", media_filename="GIF-001.gif", media_type="image")]
        md = convert(msgs, media_index=media_index, media_rel_dir="media")
        assert "![GIF-001.gif](media/GIF-001.gif)" in md


class TestConvertMultipleDates:
    def test_two_date_groups(self):
        msg1 = _make_msg("Alice", "Day 1", ts=datetime(2023, 2, 8, 10, 0))
        msg2 = _make_msg("Bob", "Day 2", ts=datetime(2023, 2, 9, 10, 0))
        md = convert([msg1, msg2])
        assert "## Wednesday, 08 February 2023" in md
        assert "## Thursday, 09 February 2023" in md

    def test_same_date_no_duplicate_heading(self):
        msg1 = _make_msg("Alice", "Hi", ts=datetime(2023, 2, 8, 10, 0))
        msg2 = _make_msg("Bob", "Hey", ts=datetime(2023, 2, 8, 11, 0))
        md = convert([msg1, msg2])
        assert md.count("## Wednesday, 08 February 2023") == 1
