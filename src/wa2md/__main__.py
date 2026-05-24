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
        help="WhatsApp export: a .zip file, a folder, or a _chat.txt chat file.",
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

    media_path: Path | None = args.media
    if media_path is not None and not media_path.exists():
        print(f"Error: media folder not found: {media_path}", file=sys.stderr)
        sys.exit(1)
    media_folder: str | None = str(media_path) if media_path is not None else None

    chat_name: str = args.chat_name or input_path.stem.replace("-", "").replace(" ", "_")
    chat_name: str = chat_name.replace("__", "_")
    chat_filename: str = "_chat.txt"
    output_path: Path = input_path / Path(chat_name).with_suffix(".md")

    # Lazy imports so startup is fast even if not needed
    from wa2md.parser import parse_text
    from wa2md.converter import convert
    from wa2md.media_handler import MediaHandler

    is_dir: bool = input_path.is_dir()
    is_zip: bool = input_path.suffix.lower() == ".zip" if not is_dir else False

    def process_export_container(kind: str) -> None:
        with MediaHandler(input_path) as media:
            file_map = media.get_file_map()
            txt_name = next(
                (name for name in file_map if name == chat_filename), None
            )
            if txt_name is None:
                print(
                    f"Error: _chat.txt file not found inside {kind}: {input_path}",
                    file=sys.stderr,
                )
                sys.exit(1)

            txt_path = file_map[txt_name]
            print(f"Parsing chat: {txt_name}")
            text = txt_path.read_text(encoding="utf-8", errors="replace")
            messages = parse_text(text)
            print(f"Converting {len(messages)} messages…")
            md = convert(messages, media=media, chat_name=chat_name)
            output_path.write_text(md, encoding="utf-8")

    # Chat content in a zip file or directory with media files.
    if is_zip:
        process_export_container("zip file")
    elif is_dir:
        process_export_container("directory")
    else:
        print(f"Parsing chat: {input_path}")
        text = input_path.read_text(encoding="utf-8", errors="replace")
        messages = parse_text(text, media_folder=media_folder)
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
