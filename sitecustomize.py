from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from pipelines import prompt

    prompt.setup()
except Exception:
    # Running in an environment where pipelines are unavailable.
    pass
