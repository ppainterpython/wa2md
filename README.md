# wa2md

![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

Convert a WhatsApp chat export (`.zip` or `.txt` + media folder) into a single Markdown page with photos, GIFs, and videos displayed inline.

---

## Features

- 📦 Accepts a WhatsApp `.zip` export or a `.txt` file with a separate media folder
- 🖼️ Embeds images and GIFs inline using standard Markdown image syntax
- 🎬 Links to videos and audio files with descriptive emoji icons
- 📅 Groups messages by date with `## Date` headings
- 💬 Supports Android (24 h & 12 h AM/PM) and iOS chat formats
- 🔗 Handles multi-line messages, system messages, and `<Media omitted>` placeholders
- 🐍 Pure Python stdlib — no third-party dependencies

---

## Installation

```bash
pip install .
```

Requires Python 3.9+.

---

## Quick Start

```bash
# From a zip export
wa2md "WhatsApp Chat with Alice.zip"

# From a txt file + media folder
wa2md _chat.txt --media ./media/ --output alice.md --chat-name "Alice"
```

### Python API

```python
from pathlib import Path
from wa2md import parse_file, convert
from wa2md.media_handler import MediaHandler

messages = parse_file(Path("_chat.txt"))
with MediaHandler(Path("./media/")) as media:
    md = convert(messages, media=media, chat_name="Alice")
Path("alice.md").write_text(md, encoding="utf-8")
```

---

## Documentation

Full documentation is in the [`docs/`](docs/README.md) folder.
