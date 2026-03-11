"""CLI entry point for wa2md."""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path


def _find_txt_in_zip(zf: zipfile.ZipFile) -> str | None:
    for name in zf.namelist():
        if name.endswith(".txt"):
            return name
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a WhatsApp chat export to Markdown.",
    )
    parser.add_argument(
        "input",
        type=Path,
        help="WhatsApp export: a .zip file or a .txt chat file.",
    )
    parser.add_argument(
        "--media",
        "-m",
        type=Path,
        default=None,
        help="Folder containing media files (ignored when input is a .zip).",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output .md file (default: same name as input with .md extension).",
    )
    parser.add_argument(
        "--chat-name",
        "-n",
        default=None,
        help="Chat name for the Markdown title (default: derived from filename).",
    )

    args = parser.parse_args()

    input_path: Path = args.input

    if not input_path.exists():
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    output_path: Path = args.output or input_path.with_suffix(".md")
    chat_name: str = args.chat_name or input_path.stem.replace("_", " ").replace("-", " ")

    # Lazy imports so startup is fast even if not needed
    from wa2md.parser import parse_text
    from wa2md.converter import convert
    from wa2md.media_handler import MediaHandler

    is_zip = input_path.suffix.lower() == ".zip"

    if is_zip:
        print(f"Opening zip: {input_path}")
        if not zipfile.is_zipfile(input_path):
            print(f"Error: {input_path} is not a valid zip file.", file=sys.stderr)
            sys.exit(1)

        with MediaHandler(input_path) as media:
            file_map = media.get_file_map()
            txt_name = next(
                (name for name in file_map if name.endswith(".txt")), None
            )
            if txt_name is None:
                print("Error: no .txt file found inside the zip.", file=sys.stderr)
                sys.exit(1)

            txt_path = file_map[txt_name]
            print(f"Parsing chat: {txt_name}")
            text = txt_path.read_text(encoding="utf-8", errors="replace")
            messages = parse_text(text)
            print(f"Converting {len(messages)} messages…")
            md = convert(messages, media=media, chat_name=chat_name)
            output_path.write_text(md, encoding="utf-8")
    else:
        print(f"Parsing chat: {input_path}")
        text = input_path.read_text(encoding="utf-8", errors="replace")
        messages = parse_text(text)
        print(f"Converting {len(messages)} messages…")

        media: MediaHandler | None = None
        if args.media:
            if not args.media.is_dir():
                print(f"Error: media path is not a directory: {args.media}", file=sys.stderr)
                sys.exit(1)
            media = MediaHandler(args.media)

        try:
            md = convert(messages, media=media, chat_name=chat_name)
        finally:
            if media is not None:
                media.cleanup()

        output_path.write_text(md, encoding="utf-8")

    print(f"Written: {output_path}")


if __name__ == "__main__":
    main()
