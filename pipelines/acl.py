from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List

# Path to ACL file. Defaults to `pipelines/acl.json` next to this module.
ACL_PATH = Path(os.getenv("PIPELINE_ACL_PATH", Path(__file__).with_name("acl.json")))

_cache: Dict[str, Any] = {"ts": 0.0, "data": {}}


def load_acl() -> Dict[str, Dict[str, List[str]]]:
    """Return ACL rules caching results for 60 seconds."""
    now = time.time()
    if _cache["data"] and now - _cache["ts"] < 60:
        return _cache["data"]
    try:
        with ACL_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                data = {}
    except Exception:
        data = {}
    _cache["ts"] = now
    _cache["data"] = data
    return data


def allowed_groups_for_user(user: Dict[str, Any] | None) -> List[str]:
    """Return list of pipeline groups allowed for the given user."""
    if not user:
        return []
    user_id = str(user.get("id", ""))
    role = str(user.get("role", ""))
    acl = load_acl()
    groups: List[str] = []
    for group, rules in acl.items():
        if not isinstance(rules, dict):
            continue
        ids = [str(u) for u in rules.get("user_ids", [])]
        roles = [str(r) for r in rules.get("roles", [])]
        if user_id in ids or role in roles:
            groups.append(group)
    return groups


def is_pipe_allowed(
    pipe_id: str, user: Dict[str, Any] | None, manifest: List[Dict[str, Any]]
) -> bool:
    """Return True if given pipe is allowed for user according to ACL and manifest."""
    allowed_groups = set(allowed_groups_for_user(user))
    for entry in manifest:
        if entry.get("id") == pipe_id and entry.get("group") in allowed_groups:
            return True
    return False


def filter_manifest_for_user(
    user: Dict[str, Any] | None, manifest: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Filter manifest entries based on user permissions."""
    allowed_groups = set(allowed_groups_for_user(user))
    return [m for m in manifest if m.get("group") in allowed_groups]
