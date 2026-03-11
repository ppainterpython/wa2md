# wa2md Documentation

## Overview

**wa2md** converts WhatsApp chat exports (`.zip` or `.txt` + media folder) into a single Markdown file with photos, GIFs, and videos displayed inline.

---

## Installation

```bash
pip install .
```

Or in editable/development mode:

```bash
pip install -e .
```

Requires Python 3.9 or later. No third-party dependencies.

---

## WhatsApp Export Instructions

### Android
1. Open the chat → ⋮ Menu → **More** → **Export chat**
2. Choose **Include media** (or **Without media**)
3. Share/save the resulting `.zip` file

### iOS
1. Open the chat → contact/group name → **Export Chat**
2. Choose **Attach Media** (or **Without Media**)
3. Save the `.zip` file

---

## Usage

### Command Line

**Convert from a zip export (recommended):**
```bash
wa2md WhatsApp\ Chat\ with\ Alice.zip
```

**Convert from a .txt file with a media folder:**
```bash
wa2md _chat.txt --media ./WhatsApp\ Chat\ with\ Alice/
```

**Specify output file and chat name:**
```bash
wa2md export.zip --output alice_chat.md --chat-name "Alice 😊"
```

**Full options:**
```
usage: wa2md [-h] [--media FOLDER] [--output FILE] [--chat-name NAME] input

positional arguments:
  input                 WhatsApp export: a .zip file or a .txt chat file.

options:
  -h, --help            show this help message and exit
  --media, -m FOLDER    Folder containing media files (ignored when input is .zip).
  --output, -o FILE     Output .md file (default: input stem + .md).
  --chat-name, -n NAME  Chat name for the Markdown title.
```

### Python API

```python
from pathlib import Path
from wa2md import parse_file, convert
from wa2md.media_handler import MediaHandler

messages = parse_file(Path("_chat.txt"))

with MediaHandler(Path("./media/")) as media:
    markdown = convert(messages, media=media, chat_name="My Chat")

Path("chat.md").write_text(markdown, encoding="utf-8")
```

---

## Output Format

```markdown
# Chat: Alice

## Wednesday, 16 January 2020

*Messages and calls are end-to-end encrypted.*
**10:00 - Alice**: Hi Bob!
**10:01 - Bob**: Hey! Check this out:
**10:02 - Bob**: ![IMG-20200116-WA0001.jpg](/path/to/IMG-20200116-WA0001.jpg)
**10:03 - Alice**: [📹 VID-20200116-WA0001.mp4](/path/to/VID-20200116-WA0001.mp4)
**10:04 - Alice**: [🔊 PTT-20200116-WA0001.opus](/path/to/PTT-20200116-WA0001.opus)
```

### Media rendering

| Type | Format | Emoji |
|------|--------|-------|
| Image (jpg, jpeg, png, gif, webp, heic, heif) | `![name](path)` | — |
| Video (mp4, mov, avi, mkv, 3gp) | `[📹 name](path)` | 📹 |
| Audio (opus, mp3, aac, m4a, ogg) | `[🔊 name](path)` | 🔊 |
| Other / not found | `[📎 name](path)` or `[📎 name - not found]` | 📎 |

---

## Supported Chat Formats

| Platform | Example |
|----------|---------|
| Android (24 h) | `16/01/2020, 14:23 - Alice: Hello` |
| Android (12 h) | `1/16/20, 2:23 PM - Alice: Hello` |
| iOS | `[16/01/2020, 14:23:45] Alice: Hello` |

Multi-line messages, system messages, and `<Media omitted>` placeholders are all handled correctly.
