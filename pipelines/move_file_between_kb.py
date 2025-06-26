from __future__ import annotations

import asyncio
from typing import Callable, Any, Dict, List


async def run(
    metadata: Dict[str, Any],
    *,
    event_emitter: Callable[[dict], Any] | None = None,
) -> Dict[str, Any]:
    """Move a file from one KB to another.

    If required metadata fields are missing, return follow_up instructions.
    """
    required = ["src_kb_id", "dst_kb_id", "file_id"]
    missing: List[str] = [field for field in required if field not in metadata]
    if missing:
        return {
            "finish_reason": "follow_up",
            "follow_up": {
                "missing_fields": missing,
                "message": "Please provide missing fields",
            },
        }

    if event_emitter:
        await event_emitter({"type": "status", "data": {"status": "running"}})

    # Placeholder move logic
    await asyncio.sleep(0)  # simulate async work

    if event_emitter:
        await event_emitter(
            {"type": "status", "data": {"status": "done", "done": True}}
        )

    return {
        "finish_reason": "stop",
        "content": {"moved": True, "file_id": metadata["file_id"]},
    }
