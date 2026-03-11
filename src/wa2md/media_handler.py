"""Handle media files from a WhatsApp export.

Supports two input modes:
1. A ``.zip`` archive (the direct export from WhatsApp) that contains a
   ``_chat.txt`` and zero or more media files in the archive root.
2. A plain ``.txt`` file accompanied by a folder of media files.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, Optional, Tuple


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def extract_zip(zip_path: str | os.PathLike, dest_dir: str | os.PathLike | None = None) -> Path:
    """Extract a WhatsApp ``.zip`` export into *dest_dir*.

    If *dest_dir* is ``None`` a temporary directory is created (the caller is
    responsible for cleaning it up).  The path to the extraction directory is
    returned.
    """
    zip_path = Path(zip_path)
    if not zip_path.is_file():
        raise FileNotFoundError(f"Zip file not found: {zip_path}")

    if dest_dir is None:
        dest = Path(tempfile.mkdtemp(prefix="wa2md_"))
    else:
        dest = Path(dest_dir)
        dest.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(dest)

    return dest


def find_chat_txt(directory: str | os.PathLike) -> Optional[Path]:
    """Locate the WhatsApp chat text file inside *directory*.

    WhatsApp names it ``_chat.txt``.  If not found, the first ``.txt`` file
    in the directory is returned as a fallback.  Returns ``None`` if no
    suitable file is found.
    """
    directory = Path(directory)
    # Prefer the canonical name
    candidate = directory / "_chat.txt"
    if candidate.is_file():
        return candidate

    # Fallback: any .txt file
    for path in sorted(directory.iterdir()):
        if path.suffix.lower() == ".txt":
            return path

    return None


def build_media_index(directory: str | os.PathLike) -> Dict[str, Path]:
    """Return a mapping of *filename → full Path* for every media file in
    *directory*.

    Only the immediate children of *directory* are indexed (WhatsApp puts all
    media in the archive root).
    """
    directory = Path(directory)
    index: Dict[str, Path] = {}
    for path in directory.iterdir():
        if path.is_file() and path.suffix.lower() != ".txt":
            index[path.name] = path
    return index


def resolve_input(
    input_path: str | os.PathLike,
    media_dir: str | os.PathLike | None = None,
) -> Tuple[str, Dict[str, Path], Optional[Path]]:
    """High-level helper that accepts either a ``.zip`` or a ``.txt`` file.

    Returns ``(chat_text, media_index, tmp_dir)`` where:

    * ``chat_text`` – the raw text content of the chat file.
    * ``media_index`` – ``{filename: full_path}`` for all media files.
    * ``tmp_dir`` – a :class:`~pathlib.Path` pointing at the temporary
      directory created for zip extraction (``None`` for txt input).  Callers
      should delete this directory when done.
    """
    input_path = Path(input_path)
    if not input_path.is_file():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    tmp_dir: Optional[Path] = None

    if input_path.suffix.lower() == ".zip":
        tmp_dir = extract_zip(input_path)
        chat_file = find_chat_txt(tmp_dir)
        if chat_file is None:
            raise ValueError(f"No chat text file found inside zip: {input_path}")
        media_index = build_media_index(tmp_dir)
        chat_text = chat_file.read_text(encoding="utf-8", errors="replace")

    elif input_path.suffix.lower() == ".txt":
        chat_text = input_path.read_text(encoding="utf-8", errors="replace")
        if media_dir is not None:
            media_index = build_media_index(media_dir)
        else:
            # Look for media next to the txt file
            media_index = build_media_index(input_path.parent)

    else:
        raise ValueError(
            f"Unsupported input file type '{input_path.suffix}'. "
            "Expected .zip or .txt."
        )

    return chat_text, media_index, tmp_dir


def cleanup_tmp(tmp_dir: Optional[Path]) -> None:
    """Remove a temporary directory created by :func:`resolve_input`."""
    if tmp_dir is not None and tmp_dir.is_dir():
        shutil.rmtree(tmp_dir, ignore_errors=True)
