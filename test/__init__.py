from __future__ import annotations

"""Test package setup."""

import sys
from pathlib import Path

# Ensure repository root is on sys.path so imports like ``test.util`` work
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
