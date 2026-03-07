"""Pytest configuration for Revenue Recovery Agent tests."""

import sys
from pathlib import Path

exports_path = Path(__file__).parent.parent.parent
if str(exports_path) not in sys.path:
    sys.path.insert(0, str(exports_path))
