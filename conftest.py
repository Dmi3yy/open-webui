from __future__ import annotations

import sys
from pathlib import Path

# Ensure repository root is first on sys.path for imports like ``test.util``
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
