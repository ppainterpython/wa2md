"""conftest.py — ensure src/ is on sys.path when running tests without install."""

import sys
from pathlib import Path

# Add src/ to path so tests can import wa2md even without `pip install -e .`
src = Path(__file__).parent.parent / "src"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))
