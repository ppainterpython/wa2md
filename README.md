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

## Local Setup Notes

Using a virtual environment with VS Code is convenient. There are different ways to set it up. Here is how I do it.

I store the virtual environments in `~/venvs` using a bash shell on Windows. Then create a `.env` file in the project root folder with something like this:

```text
VIRTUAL_ENV = ~/venvs/p3-py3.14

```

Also, set the interpreter with the python command in vs code.

Then using the following in the `launch.json` debugger setup file.

```json
{
    // Use IntelliSense to learn about possible attributes.
    // Hover to view descriptions of existing attributes.
    // For more information, visit: https://go.microsoft.com/fwlink/?linkid=830387
    "version": "0.2.0",
    "configurations": [

        {
            "name": "Python Debugger: Current File",
            "type": "debugpy",
            "request": "launch",
            "program": "${file}",
            "args": ["c:\\users\\ppain\\temp\\WhatsApp Chat - Alyssa Garcia.zip"],
            "console": "integratedTerminal",
            "envFile": "${workspaceFolder}/.env",
            "env": {
                "PYTHONPATH": "${workspaceFolder};${workspaceFolder}/src"
            }
        }
    ]
}```
