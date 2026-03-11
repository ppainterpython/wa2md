"""Command-line interface for wa2md.

Usage examples::

    # Convert a WhatsApp .zip export
    wa2md chat.zip -o chat.md

    # Convert a .txt export with a separate media folder
    wa2md _chat.txt --media-dir ./WhatsApp_Media -o chat.md

    # Use a custom document title
    wa2md chat.zip -t "My Chat with Alice" -o alice.md

    # Place generated media references under a custom sub-directory
    wa2md chat.zip --media-rel-dir attachments -o chat.md
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

from .media_handler import resolve_input, cleanup_tmp
from .parser import parse_chat
from .converter import convert


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="wa2md",
        description="Convert a WhatsApp chat export (.zip or .txt) to Markdown.",
    )
    p.add_argument(
        "input",
        metavar="INPUT",
        help="Path to the WhatsApp export file (.zip or .txt).",
    )
    p.add_argument(
        "-o",
        "--output",
        metavar="OUTPUT",
        default=None,
        help=(
            "Path for the output Markdown file. "
            "Defaults to the input filename with a .md extension."
        ),
    )
    p.add_argument(
        "-m",
        "--media-dir",
        metavar="MEDIA_DIR",
        default=None,
        help=(
            "Folder containing media files (only used when INPUT is a .txt file). "
            "Defaults to the same directory as the .txt file."
        ),
    )
    p.add_argument(
        "--media-rel-dir",
        metavar="REL_DIR",
        default="media",
        help=(
            "Relative directory prefix used for media references inside the "
            "generated Markdown.  Defaults to 'media'."
        ),
    )
    p.add_argument(
        "-t",
        "--title",
        metavar="TITLE",
        default=None,
        help="Document title (H1 heading).  Defaults to the input filename stem.",
    )
    p.add_argument(
        "--copy-media",
        action="store_true",
        help=(
            "Copy media files referenced in the chat into a sub-directory "
            "next to the output Markdown file."
        ),
    )
    return p


def main(argv=None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    if not input_path.is_file():
        print(f"wa2md: error: input file not found: {input_path}", file=sys.stderr)
        return 1

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_suffix(".md")

    # Determine document title
    title = args.title or input_path.stem

    tmp_dir = None
    try:
        chat_text, media_index, tmp_dir = resolve_input(
            input_path,
            media_dir=args.media_dir,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"wa2md: error: {exc}", file=sys.stderr)
        return 1

    # Parse and convert
    messages = parse_chat(chat_text)
    markdown = convert(
        messages,
        title=title,
        media_index=media_index,
        media_rel_dir=args.media_rel_dir,
    )

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    print(f"Written: {output_path}")

    # Optionally copy media files alongside the output
    if args.copy_media and media_index:
        media_dest = output_path.parent / args.media_rel_dir
        media_dest.mkdir(parents=True, exist_ok=True)
        copied = 0
        for fname, src in media_index.items():
            dest_file = media_dest / fname
            if not dest_file.exists():
                shutil.copy2(src, dest_file)
            copied += 1
        print(f"Copied {copied} media file(s) to: {media_dest}")

    cleanup_tmp(tmp_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
