"""wa2md – Convert WhatsApp chat exports to Markdown."""
__author__ = "Paul Painter"
__copyright__ = "2026 Paul Painter"
__name__ = "wa3md"
__description__ = "WhatsApp to Markdown converter"
__license__ = "MIT"


from .parser import Message, parse_file, parse_text
from .converter import convert
from .media_handler import MediaHandler

__all__ = ["Message", "parse_file", "parse_text", "convert", "MediaHandler"]
