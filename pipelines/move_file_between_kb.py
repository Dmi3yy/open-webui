from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from tools.openwebui_tool import Tools


async def run(
    metadata: Dict[str, Any],
    *,
    event_emitter: Callable[[dict], Any] | None = None,
    user: Optional[dict] = None,
) -> Dict[str, Any]:
    """Move a file from one KB to another using the WebUI API."""

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

    emitter = event_emitter
    if emitter:
        await emitter({"type": "status", "data": {"status": "validating"}})

    tools = Tools()

    await tools.add_file_to_knowledge(
        metadata["dst_kb_id"],
        metadata["file_id"],
        __user__=user,
        __event_emitter__=event_emitter,
    )

    await tools.remove_file_from_knowledge(
        metadata["src_kb_id"],
        metadata["file_id"],
        __user__=user,
        __event_emitter__=event_emitter,
    )

    if emitter:
        await emitter({"type": "status", "data": {"status": "done", "done": True}})

    return {
        "finish_reason": "stop",
        "content": {
            "moved": True,
            "file_id": metadata["file_id"],
            "dst_kb_id": metadata["dst_kb_id"],
        },
    }
