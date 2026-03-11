# wa2md

Convert a WhatsApp chat export (`.zip` or `.txt`) to a Markdown page that
displays photos, GIFs, and videos inline.

## Quick start

```bash
pip install .
wa2md "WhatsApp Chat with Alice.zip" -o alice_chat.md
```

See [docs/README.md](docs/README.md) for full documentation.

## Features

- Parses both Android and iOS export formats (12 h / 24 h, multiple date separators)
- Embeds images and GIFs with `![alt](path)` Markdown syntax
- Embeds videos with an HTML `<video>` element
- Embeds audio messages with an HTML `<audio>` element
- Groups messages by date with heading separators
- Handles multi-line messages, system messages, and media-omitted notices
- Works with `.zip` archives or a plain `.txt` + media folder

## Development

```bash
pip install pytest
pytest
```
