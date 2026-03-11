"""Unit tests for wa2md.parser."""

from __future__ import annotations

from datetime import datetime

import pytest

from wa2md.parser import (
    Message,
    _detect_media,
    _parse_timestamp,
    parse_chat,
)


# ---------------------------------------------------------------------------
# _parse_timestamp
# ---------------------------------------------------------------------------


class TestParseTimestamp:
    def test_android_24h(self):
        dt = _parse_timestamp("08/02/2023, 14:30")
        assert dt == datetime(2023, 2, 8, 14, 30)

    def test_android_24h_with_seconds(self):
        dt = _parse_timestamp("08/02/2023, 14:30:15")
        assert dt == datetime(2023, 2, 8, 14, 30, 15)

    def test_ios_12h_pm(self):
        dt = _parse_timestamp("08/02/2023, 2:30 PM")
        assert dt == datetime(2023, 2, 8, 14, 30)

    def test_two_digit_year(self):
        dt = _parse_timestamp("08/02/23, 14:30")
        assert dt == datetime(2023, 2, 8, 14, 30)

    def test_dot_separator(self):
        dt = _parse_timestamp("08.02.2023, 14:30")
        assert dt == datetime(2023, 2, 8, 14, 30)

    def test_unknown_format_returns_none(self):
        dt = _parse_timestamp("not a timestamp")
        assert dt is None


# ---------------------------------------------------------------------------
# _detect_media
# ---------------------------------------------------------------------------


class TestDetectMedia:
    def test_attached_bracket_image(self):
        fname, mtype = _detect_media("<attached: IMG-20230208-WA0001.jpg>")
        assert fname == "IMG-20230208-WA0001.jpg"
        assert mtype == "image"

    def test_attached_suffix_video(self):
        fname, mtype = _detect_media("VID-20230208-WA0001.mp4 (file attached)")
        assert fname == "VID-20230208-WA0001.mp4"
        assert mtype == "video"

    def test_attached_suffix_gif(self):
        fname, mtype = _detect_media("GIF-20230208-WA0001.gif (file attached)")
        assert fname == "GIF-20230208-WA0001.gif"
        assert mtype == "image"

    def test_attached_audio(self):
        fname, mtype = _detect_media("PTT-20230208-WA0001.opus (file attached)")
        assert fname == "PTT-20230208-WA0001.opus"
        assert mtype == "audio"

    def test_image_omitted(self):
        fname, mtype = _detect_media("image omitted")
        assert fname is None
        assert mtype == "image"

    def test_video_omitted(self):
        fname, mtype = _detect_media("video omitted")
        assert fname is None
        assert mtype == "video"

    def test_media_omitted_generic(self):
        fname, mtype = _detect_media("<Media omitted>")
        assert fname is None
        assert mtype == "document"

    def test_plain_text_no_media(self):
        fname, mtype = _detect_media("Hello, how are you?")
        assert fname is None
        assert mtype is None

    def test_zero_width_prefix_stripped(self):
        # WhatsApp sometimes prepends a zero-width left-to-right mark
        fname, mtype = _detect_media("\u200eIMG-001.jpg (file attached)")
        assert fname == "IMG-001.jpg"
        assert mtype == "image"


# ---------------------------------------------------------------------------
# parse_chat – Android format
# ---------------------------------------------------------------------------


ANDROID_CHAT = """\
08/02/2023, 14:30 - Alice: Hello Bob!
08/02/2023, 14:31 - Bob: Hi Alice!
08/02/2023, 14:32 - Alice: How are you doing today?
This is a second line of the same message.
08/02/2023, 14:33 - Bob: IMG-20230208-WA0001.jpg (file attached)
08/02/2023, 14:34 - Messages and calls are end-to-end encrypted.
"""


class TestParseChatAndroid:
    def setup_method(self):
        self.messages = parse_chat(ANDROID_CHAT)

    def test_message_count(self):
        assert len(self.messages) == 5

    def test_first_message(self):
        msg = self.messages[0]
        assert msg.sender == "Alice"
        assert msg.content == "Hello Bob!"
        assert msg.timestamp == datetime(2023, 2, 8, 14, 30)
        assert not msg.is_system

    def test_multiline_message(self):
        msg = self.messages[2]
        assert msg.sender == "Alice"
        assert "second line" in msg.content

    def test_media_message(self):
        msg = self.messages[3]
        assert msg.sender == "Bob"
        assert msg.media_filename == "IMG-20230208-WA0001.jpg"
        assert msg.media_type == "image"

    def test_system_message(self):
        msg = self.messages[4]
        assert msg.is_system
        assert msg.sender is None


# ---------------------------------------------------------------------------
# parse_chat – iOS format
# ---------------------------------------------------------------------------


IOS_CHAT = """\
[08/02/2023, 14:30:15] Alice: Hello from iOS!
[08/02/2023, 14:31:00] Bob: Hey!
[08/02/2023, 14:32:05] Alice: <attached: VID-20230208-WA0001.mp4>
"""


class TestParseChatIOS:
    def setup_method(self):
        self.messages = parse_chat(IOS_CHAT)

    def test_message_count(self):
        assert len(self.messages) == 3

    def test_sender_and_content(self):
        msg = self.messages[0]
        assert msg.sender == "Alice"
        assert msg.content == "Hello from iOS!"

    def test_video_attachment(self):
        msg = self.messages[2]
        assert msg.media_filename == "VID-20230208-WA0001.mp4"
        assert msg.media_type == "video"


# ---------------------------------------------------------------------------
# parse_chat – edge cases
# ---------------------------------------------------------------------------


class TestParseChatEdgeCases:
    def test_empty_string(self):
        assert parse_chat("") == []

    def test_no_messages(self):
        # Lines that don't match any pattern
        assert parse_chat("This is not a chat file.\nJust some text.") == []

    def test_bom_prefix_ignored(self):
        # BOM at start of file should not break parsing
        text = "\ufeff08/02/2023, 14:30 - Alice: Hi\n"
        msgs = parse_chat(text)
        assert len(msgs) == 1
        assert msgs[0].sender == "Alice"

    def test_12h_format(self):
        text = "08/02/2023, 2:30 PM - Alice: Afternoon!\n"
        msgs = parse_chat(text)
        assert len(msgs) == 1
        assert msgs[0].timestamp == datetime(2023, 2, 8, 14, 30)

    def test_omitted_gif_in_message(self):
        text = "08/02/2023, 14:30 - Alice: GIF omitted\n"
        msgs = parse_chat(text)
        assert msgs[0].media_type == "image"
        assert msgs[0].media_filename is None
