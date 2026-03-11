"""Tests for wa2md.media_handler."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from wa2md.media_handler import MediaHandler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_zip(tmp_path: Path, files: dict[str, bytes]) -> Path:
    zip_path = tmp_path / "export.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return zip_path


# ---------------------------------------------------------------------------
# Folder source
# ---------------------------------------------------------------------------

class TestFolderSource:
    def test_get_file_map_keys(self, tmp_path):
        (tmp_path / "photo.jpg").write_bytes(b"img")
        (tmp_path / "clip.mp4").write_bytes(b"vid")
        handler = MediaHandler(tmp_path)
        fmap = handler.get_file_map()
        assert "photo.jpg" in fmap
        assert "clip.mp4" in fmap

    def test_get_file_map_paths_are_absolute(self, tmp_path):
        (tmp_path / "img.png").write_bytes(b"x")
        handler = MediaHandler(tmp_path)
        fmap = handler.get_file_map()
        assert fmap["img.png"].is_absolute()

    def test_get_file_map_empty_folder(self, tmp_path):
        handler = MediaHandler(tmp_path)
        assert handler.get_file_map() == {}


# ---------------------------------------------------------------------------
# Zip source
# ---------------------------------------------------------------------------

class TestZipSource:
    def test_get_file_map_from_zip(self, tmp_path):
        zip_path = _create_zip(tmp_path, {
            "photo.jpg": b"img data",
            "_chat.txt": b"chat text",
        })
        with MediaHandler(zip_path) as handler:
            fmap = handler.get_file_map()
        assert "photo.jpg" in fmap
        assert "_chat.txt" in fmap

    def test_zip_extracted_content(self, tmp_path):
        zip_path = _create_zip(tmp_path, {"note.txt": b"hello"})
        with MediaHandler(zip_path) as handler:
            fmap = handler.get_file_map()
            assert fmap["note.txt"].read_bytes() == b"hello"

    def test_context_manager_cleanup(self, tmp_path):
        zip_path = _create_zip(tmp_path, {"a.jpg": b"x"})
        handler = MediaHandler(zip_path)
        with handler:
            fmap = handler.get_file_map()
            extracted_path = fmap["a.jpg"]
        # After exit, the temp dir is gone
        assert not extracted_path.exists()


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

class TestClassify:
    @pytest.fixture
    def handler(self, tmp_path):
        return MediaHandler(tmp_path)

    @pytest.mark.parametrize("filename", ["photo.jpg", "img.jpeg", "img.png", "img.gif", "img.webp", "img.heic", "img.heif"])
    def test_image(self, handler, filename):
        assert handler.classify(filename) == "image"

    @pytest.mark.parametrize("filename", ["clip.mp4", "clip.mov", "clip.avi", "clip.mkv", "clip.3gp"])
    def test_video(self, handler, filename):
        assert handler.classify(filename) == "video"

    @pytest.mark.parametrize("filename", ["voice.opus", "audio.mp3", "audio.aac", "audio.m4a", "audio.ogg"])
    def test_audio(self, handler, filename):
        assert handler.classify(filename) == "audio"

    @pytest.mark.parametrize("filename", ["doc.pdf", "file.zip", "data.csv", "unknown"])
    def test_unknown(self, handler, filename):
        assert handler.classify(filename) == "unknown"


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------

class TestContextManager:
    def test_enter_returns_self(self, tmp_path):
        handler = MediaHandler(tmp_path)
        with handler as h:
            assert h is handler

    def test_cleanup_called_on_exit(self, tmp_path):
        zip_path = _create_zip(tmp_path, {"img.jpg": b"data"})
        handler = MediaHandler(zip_path)
        with handler:
            _ = handler.get_file_map()
            tmpdir = handler._tmpdir
        # TemporaryDirectory should be cleaned up
        assert handler._tmpdir is None
        assert handler._file_map is None

    def test_double_cleanup_safe(self, tmp_path):
        handler = MediaHandler(tmp_path)
        handler.cleanup()
        handler.cleanup()  # should not raise
