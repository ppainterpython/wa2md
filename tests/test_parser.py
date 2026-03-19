"""Tests for wa2md.parser."""

from __future__ import annotations

from datetime import datetime

import pytest

from wa2md.parser import Message, parse_text, parse_file


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def android_24h_single():
    return "16/01/2020, 14:23 - Alice: Hello there"


@pytest.fixture
def android_12h_single():
    return "1/16/20, 2:23 PM - Alice: Hello there"


@pytest.fixture
def ios_single():
    return "[16/01/2020, 14:23:45] Alice: Hello there"


# ---------------------------------------------------------------------------
# Android 24 h format
# ---------------------------------------------------------------------------

class TestAndroid24h:
    def test_basic(self, android_24h_single):
        msgs = parse_text(android_24h_single)
        assert len(msgs) == 1
        msg = msgs[0]
        assert msg.sender == "Alice"
        assert msg.content == "Hello there"
        assert msg.timestamp == datetime(2020, 1, 16, 14, 23)

    def test_timestamp_fields(self):
        msgs = parse_text("31/12/2021, 23:59 - Bob: Night")
        assert msgs[0].timestamp.day == 31
        assert msgs[0].timestamp.month == 12
        assert msgs[0].timestamp.year == 2021
        assert msgs[0].timestamp.hour == 23
        assert msgs[0].timestamp.minute == 59

    def test_no_media(self, android_24h_single):
        msgs = parse_text(android_24h_single)
        assert msgs[0].media_filename is None


# ---------------------------------------------------------------------------
# Android 12 h AM/PM format
# ---------------------------------------------------------------------------

class TestAndroid12h:
    def test_pm(self, android_12h_single):
        msgs = parse_text(android_12h_single)
        assert len(msgs) == 1
        msg = msgs[0]
        assert msg.sender == "Alice"
        assert msg.content == "Hello there"
        assert msg.timestamp.hour == 14
        assert msg.timestamp.minute == 23

    def test_am(self):
        msgs = parse_text("3/5/22, 9:05 AM - Carol: Morning!")
        assert msgs[0].timestamp.hour == 9

    def test_noon(self):
        msgs = parse_text("3/5/22, 12:00 PM - Carol: Noon")
        assert msgs[0].timestamp.hour == 12


# ---------------------------------------------------------------------------
# iOS format
# ---------------------------------------------------------------------------

class TestIOS:
    def test_basic(self, ios_single):
        msgs = parse_text(ios_single)
        assert len(msgs) == 1
        msg = msgs[0]
        assert msg.sender == "Alice"
        assert msg.content == "Hello there"
        assert msg.timestamp == datetime(2020, 1, 16, 14, 23, 45)

    def test_without_seconds(self):
        msgs = parse_text("[16/01/2020, 14:23] Alice: Hi")
        assert msgs[0].timestamp.minute == 23


# ---------------------------------------------------------------------------
# Multi-line messages
# ---------------------------------------------------------------------------

class TestMultiLine:
    def test_continuation(self):
        text = (
            "16/01/2020, 14:23 - Alice: Line one\n"
            "Line two\n"
            "Line three"
        )
        msgs = parse_text(text)
        assert len(msgs) == 1
        assert "Line one" in msgs[0].content
        assert "Line two" in msgs[0].content
        assert "Line three" in msgs[0].content

    def test_two_messages_with_continuation(self):
        text = (
            "16/01/2020, 14:23 - Alice: First\n"
            "continued\n"
            "16/01/2020, 14:24 - Bob: Second"
        )
        msgs = parse_text(text)
        assert len(msgs) == 2
        assert "continued" in msgs[0].content
        assert msgs[1].sender == "Bob"


# ---------------------------------------------------------------------------
# Media omitted
# ---------------------------------------------------------------------------

class TestMediaOmitted:
    def test_angle_bracket(self):
        msgs = parse_text("16/01/2020, 14:23 - Alice: \u200e<Media omitted>")
        assert msgs[0].media_filename is None
        assert "<Media omitted>" in msgs[0].content or "Media omitted" in msgs[0].content

    def test_image_omitted(self):
        msgs = parse_text("16/01/2020, 14:23 - Alice: image omitted")
        assert msgs[0].media_filename is None

    def test_video_omitted(self):
        msgs = parse_text("16/01/2020, 14:23 - Alice: video omitted")
        assert msgs[0].media_filename is None

    def test_gif_omitted(self):
        msgs = parse_text("16/01/2020, 14:23 - Alice: GIF omitted")
        assert msgs[0].media_filename is None

    def test_audio_omitted(self):
        msgs = parse_text("16/01/2020, 14:23 - Alice: audio omitted")
        assert msgs[0].media_filename is None


# ---------------------------------------------------------------------------
# File attached
# ---------------------------------------------------------------------------

class TestFileAttached:
    def test_img_file_attached(self):
        msgs = parse_text(
            "16/01/2020, 14:23 - Alice: \u200eIMG-20200116-WA0001.jpg (file attached)"
        )
        assert msgs[0].media_filename == "IMG-20200116-WA0001.jpg"

    def test_plain_file_attached(self):
        msgs = parse_text(
            "16/01/2020, 14:23 - Alice: IMG-20200116-WA0001.jpg (file attached)"
        )
        assert msgs[0].media_filename == "IMG-20200116-WA0001.jpg"

    def test_video_file_attached(self):
        msgs = parse_text(
            "16/01/2020, 14:23 - Alice: VID-20200116-WA0001.mp4 (file attached)"
        )
        assert msgs[0].media_filename == "VID-20200116-WA0001.mp4"


# ---------------------------------------------------------------------------
# System messages
# ---------------------------------------------------------------------------

class TestSystemMessages:
    def test_encrypted_notice(self):
        text = (
            "16/01/2020, 09:00 - Messages and calls are end-to-end encrypted. "
            "No one outside of this chat, not even WhatsApp, can read or listen to them."
        )
        msgs = parse_text(text)
        assert len(msgs) == 1
        assert msgs[0].sender is None

    def test_joined_group(self):
        text = "16/01/2020, 09:01 - Alice joined using this group's invite link"
        msgs = parse_text(text)
        assert msgs[0].sender is None

    def test_system_message_has_content(self):
        text = "16/01/2020, 09:00 - You were added"
        msgs = parse_text(text)
        assert msgs[0].content == "You were added"


# ---------------------------------------------------------------------------
# parse_text with multiple messages
# ---------------------------------------------------------------------------

class TestParseText:
    CHAT = (
        "16/01/2020, 09:00 - Messages and calls are end-to-end encrypted.\n"
        "16/01/2020, 10:00 - Alice: Hi Bob!\n"
        "16/01/2020, 10:01 - Bob: Hey Alice!\n"
        "16/01/2020, 10:02 - Alice: \u200eIMG-20200116-WA0001.jpg (file attached)\n"
        "17/01/2020, 08:00 - Alice: Good morning\n"
    )

    def test_message_count(self):
        msgs = parse_text(self.CHAT)
        assert len(msgs) == 5

    def test_senders(self):
        msgs = parse_text(self.CHAT)
        assert msgs[0].sender is None
        assert msgs[1].sender == "Alice"
        assert msgs[2].sender == "Bob"

    def test_media_filename(self):
        msgs = parse_text(self.CHAT)
        assert msgs[3].media_filename == "IMG-20200116-WA0001.jpg"

    def test_dates_span_two_days(self):
        msgs = parse_text(self.CHAT)
        assert msgs[0].timestamp.day == 16
        assert msgs[4].timestamp.day == 17


# ---------------------------------------------------------------------------
# parse_file
# ---------------------------------------------------------------------------

def test_parse_file(tmp_path):
    chat_file = tmp_path / "chat.txt"
    chat_file.write_text("16/01/2020, 10:00 - Alice: Hello from file\n", encoding="utf-8")
    msgs = parse_file(chat_file)
    assert len(msgs) == 1
    assert msgs[0].sender == "Alice"
    assert msgs[0].content == "Hello from file"


def test_parse_file_empty(tmp_path):
    chat_file = tmp_path / "empty.txt"
    chat_file.write_text("", encoding="utf-8")
    msgs = parse_file(chat_file)
    assert msgs == []
