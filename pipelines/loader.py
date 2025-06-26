import json
import time
from pathlib import Path
from typing import Any, List, Dict

_MANIFEST_PATH = Path(__file__).with_name("manifest.json")
_cache: Dict[str, Any] = {"ts": 0.0, "data": []}


def load_manifest() -> List[Dict[str, Any]]:
    """Return list of pipeline definitions caching results for 60s."""
    now = time.time()
    if _cache["data"] and now - _cache["ts"] < 60:
        return _cache["data"]
    try:
        with _MANIFEST_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = []
    _cache["ts"] = now
    _cache["data"] = data
    return data
