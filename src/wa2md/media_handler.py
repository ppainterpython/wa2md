"""Handle media files from WhatsApp exports (zip or folder)."""

from __future__ import annotations

import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Optional

_IMAGE_EXTS = {"jpg", "jpeg", "png", "gif", "webp", "heic", "heif"}
_VIDEO_EXTS = {"mp4", "mov", "avi", "mkv", "3gp"}
_AUDIO_EXTS = {"opus", "mp3", "aac", "m4a", "ogg"}


class MediaHandler:
    """Provide a unified interface to media files from a zip or folder."""

    def __init__(self, source: Path) -> None:
        self._source = source
        self._tmpdir: Optional[tempfile.TemporaryDirectory[str]] = None
        self._media_dir: Optional[Path] = None
        self._file_map: Optional[dict[str, Path]] = None

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> "MediaHandler":
        return self

    def __exit__(self, *_) -> None:
        self.cleanup()

    def cleanup(self) -> None:
        if self._tmpdir is not None:
            self._tmpdir.cleanup()
            self._tmpdir = None
            self._media_dir = None
            self._file_map = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        if self._file_map is not None:
            return
        if self._source.suffix.lower() == ".zip":
            self._tmpdir = tempfile.TemporaryDirectory(prefix="wa2md_")
            dest = Path(self._tmpdir.name)
            with zipfile.ZipFile(self._source, "r") as zf:
                zf.extractall(dest)
            self._media_dir = dest
        else:
            self._media_dir = self._source
        self._file_map = self._build_map(self._media_dir)

    @staticmethod
    def _build_map(folder: Path) -> dict[str, Path]:
        result: dict[str, Path] = {}
        for p in folder.rglob("*"):
            if p.is_file():
                result[p.name] = p.resolve()
        return result

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_file_map(self) -> dict[str, Path]:
        """Return {filename: absolute_path} for all media files."""
        self._ensure_loaded()
        assert self._file_map is not None
        return dict(self._file_map)

    def classify(self, filename: str) -> str:
        """Return 'image', 'video', 'audio', or 'unknown'."""
        ext = Path(filename).suffix.lstrip(".").lower()
        if ext in _IMAGE_EXTS:
            return "image"
        if ext in _VIDEO_EXTS:
            return "video"
        if ext in _AUDIO_EXTS:
            return "audio"
        return "unknown"
