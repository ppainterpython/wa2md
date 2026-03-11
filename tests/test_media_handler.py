"""Unit tests for wa2md.media_handler."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from wa2md.media_handler import (
    build_media_index,
    cleanup_tmp,
    extract_zip,
    find_chat_txt,
    resolve_input,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_zip(dest: Path, chat_content: str, media_files: dict) -> Path:
    """Create a minimal WhatsApp-style zip at *dest/export.zip*."""
    zip_path = dest / "export.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("_chat.txt", chat_content)
        for name, data in media_files.items():
            zf.writestr(name, data)
    return zip_path


# ---------------------------------------------------------------------------
# extract_zip
# ---------------------------------------------------------------------------


class TestExtractZip:
    def test_extracts_files(self, tmp_path):
        zip_path = _make_zip(tmp_path, "hello", {"pic.jpg": b"jpg-data"})
        out = extract_zip(zip_path)
        assert (out / "_chat.txt").read_text() == "hello"
        assert (out / "pic.jpg").read_bytes() == b"jpg-data"
        cleanup_tmp(out)

    def test_custom_dest(self, tmp_path):
        zip_path = _make_zip(tmp_path, "hi", {})
        dest = tmp_path / "out"
        out = extract_zip(zip_path, dest_dir=dest)
        assert out == dest
        assert (dest / "_chat.txt").exists()

    def test_file_not_found_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            extract_zip(tmp_path / "nonexistent.zip")


# ---------------------------------------------------------------------------
# find_chat_txt
# ---------------------------------------------------------------------------


class TestFindChatTxt:
    def test_finds_canonical_name(self, tmp_path):
        chat = tmp_path / "_chat.txt"
        chat.write_text("msg")
        assert find_chat_txt(tmp_path) == chat

    def test_fallback_to_first_txt(self, tmp_path):
        other = tmp_path / "WhatsApp_Chat.txt"
        other.write_text("msg")
        result = find_chat_txt(tmp_path)
        assert result == other

    def test_returns_none_when_no_txt(self, tmp_path):
        (tmp_path / "pic.jpg").write_bytes(b"data")
        assert find_chat_txt(tmp_path) is None


# ---------------------------------------------------------------------------
# build_media_index
# ---------------------------------------------------------------------------


class TestBuildMediaIndex:
    def test_indexes_media_files(self, tmp_path):
        (tmp_path / "_chat.txt").write_text("chat")
        (tmp_path / "IMG-001.jpg").write_bytes(b"jpg")
        (tmp_path / "VID-001.mp4").write_bytes(b"mp4")
        index = build_media_index(tmp_path)
        assert "IMG-001.jpg" in index
        assert "VID-001.mp4" in index

    def test_excludes_txt_files(self, tmp_path):
        (tmp_path / "_chat.txt").write_text("chat")
        (tmp_path / "IMG-001.jpg").write_bytes(b"jpg")
        index = build_media_index(tmp_path)
        assert "_chat.txt" not in index

    def test_empty_directory(self, tmp_path):
        assert build_media_index(tmp_path) == {}


# ---------------------------------------------------------------------------
# resolve_input – zip
# ---------------------------------------------------------------------------


class TestResolveInputZip:
    def test_zip_returns_chat_text_and_media(self, tmp_path):
        chat_text = "08/02/2023, 14:30 - Alice: Hello"
        zip_path = _make_zip(tmp_path, chat_text, {"IMG-001.jpg": b"jpg"})
        text, index, tmp_dir = resolve_input(zip_path)
        try:
            assert chat_text in text
            assert "IMG-001.jpg" in index
        finally:
            cleanup_tmp(tmp_dir)

    def test_zip_no_chat_txt_raises(self, tmp_path):
        zip_path = tmp_path / "empty.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("pic.jpg", b"data")
        with pytest.raises(ValueError, match="No chat text file"):
            resolve_input(zip_path)


# ---------------------------------------------------------------------------
# resolve_input – txt
# ---------------------------------------------------------------------------


class TestResolveInputTxt:
    def test_txt_reads_chat(self, tmp_path):
        chat_file = tmp_path / "_chat.txt"
        chat_file.write_text("08/02/2023, 14:30 - Alice: Hi")
        (tmp_path / "IMG-001.jpg").write_bytes(b"jpg")
        text, index, tmp_dir = resolve_input(chat_file)
        assert tmp_dir is None
        assert "Alice: Hi" in text
        assert "IMG-001.jpg" in index

    def test_txt_with_explicit_media_dir(self, tmp_path):
        chat_file = tmp_path / "_chat.txt"
        chat_file.write_text("msg")
        media_dir = tmp_path / "media"
        media_dir.mkdir()
        (media_dir / "VID-001.mp4").write_bytes(b"mp4")
        text, index, _ = resolve_input(chat_file, media_dir=media_dir)
        assert "VID-001.mp4" in index

    def test_unsupported_extension_raises(self, tmp_path):
        f = tmp_path / "chat.json"
        f.write_text("{}")
        with pytest.raises(ValueError, match="Unsupported"):
            resolve_input(f)

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            resolve_input(tmp_path / "ghost.zip")


# ---------------------------------------------------------------------------
# cleanup_tmp
# ---------------------------------------------------------------------------


class TestCleanupTmp:
    def test_removes_directory(self, tmp_path):
        d = tmp_path / "temp"
        d.mkdir()
        (d / "file.txt").write_text("x")
        cleanup_tmp(d)
        assert not d.exists()

    def test_none_is_safe(self):
        cleanup_tmp(None)  # should not raise
