# wa2md Documentation

## Overview

**wa2md** converts WhatsApp chat exports (`.zip` archives or `.txt` files) into
readable Markdown documents.  Photos, GIFs, and videos found in the export are
embedded directly in the output so the chat history can be browsed in any
Markdown viewer or rendered as an HTML page.

---

## Installation

```bash
pip install .
```

Or, for development:

```bash
pip install -e ".[dev]"
```

---

## Quick start

### From a .zip export

Export your chat from WhatsApp (**Chat info → Export Chat → Include media**),
then run:

```bash
wa2md WhatsApp\ Chat\ with\ Alice.zip -o alice_chat.md
```

This will:
1. Extract the archive.
2. Parse `_chat.txt`.
3. Write `alice_chat.md` with all photos, GIFs, and videos referenced inline.

### From a .txt + media folder

If you extracted the archive yourself:

```bash
wa2md _chat.txt --media-dir ./WhatsApp_Chat_with_Alice -o alice_chat.md
```

---

## CLI reference

```
wa2md [-h] [-o OUTPUT] [-m MEDIA_DIR] [--media-rel-dir REL_DIR]
      [-t TITLE] [--copy-media]
      INPUT
```

| Argument | Description |
|---|---|
| `INPUT` | Path to the WhatsApp export (`.zip` or `.txt`). |
| `-o OUTPUT` | Output Markdown file path. Defaults to `<input>.md`. |
| `-m MEDIA_DIR` | Folder with media files (`.txt` input only). |
| `--media-rel-dir REL_DIR` | Prefix used for media paths inside the Markdown (default: `media`). |
| `-t TITLE` | Document title (H1 heading). Defaults to the input filename stem. |
| `--copy-media` | Copy referenced media files into `<output-dir>/<media-rel-dir>/`. |

---

## Output format

The generated Markdown looks like:

```markdown
# WhatsApp Chat with Alice

## Wednesday, 08 February 2023

**Alice** `14:30`

> Hello! 😊

**Bob** `14:31`

> ![IMG-20230208-WA0001.jpg](media/IMG-20230208-WA0001.jpg)

**Alice** `14:32`

> <video controls width="480" src="media/VID-20230208-WA0001.mp4">…</video>
```

---

## Supported media types

| Type | Extensions | Rendered as |
|---|---|---|
| Image | `.jpg` `.jpeg` `.png` `.gif` `.webp` `.heic` `.bmp` `.tiff` | Inline `![alt](path)` |
| Video | `.mp4` `.mov` `.avi` `.mkv` `.3gp` `.webm` | HTML `<video>` element |
| Audio | `.opus` `.ogg` `.mp3` `.m4a` `.aac` `.wav` | HTML `<audio>` element |
| Other | anything else | Hyperlink |

---

## Supported chat formats

| Platform | Example timestamp | Notes |
|---|---|---|
| Android | `08/02/2023, 14:30 - Sender: …` | 12 h and 24 h |
| iOS | `[08/02/2023, 14:30:15] Sender: …` | 12 h and 24 h |
| Android (German) | `08.02.23, 14:30 - Sender: …` | Dot-separated date |

Multi-line messages and system messages (group events, encryption notices) are
handled automatically.

---

## Python API

```python
from wa2md import parse_chat, convert
from wa2md.media_handler import resolve_input, cleanup_tmp

chat_text, media_index, tmp_dir = resolve_input("export.zip")
try:
    messages = parse_chat(chat_text)
    markdown = convert(messages, title="My Chat", media_index=media_index)
    print(markdown)
finally:
    cleanup_tmp(tmp_dir)
```

---

## Development

### Running tests

```bash
pip install pytest
pytest
```

### Project structure

```
wa2md/
├── src/
│   └── wa2md/
│       ├── __init__.py          # Public API
│       ├── __main__.py          # CLI entry point
│       ├── converter.py         # Markdown generation
│       ├── media_handler.py     # Zip extraction and media indexing
│       └── parser.py            # Chat text parser
├── tests/
│   ├── test_converter.py
│   ├── test_media_handler.py
│   └── test_parser.py
├── docs/
│   └── README.md                # This file
├── pyproject.toml
└── README.md
```
