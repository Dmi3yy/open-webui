"""Run registered pipelines via HTTP."""

from __future__ import annotations

import json
import os
from typing import Any, Callable, Optional

import aiohttp

from open_webui.env import AIOHTTP_CLIENT_TIMEOUT, AIOHTTP_CLIENT_SESSION_SSL
from pipelines.loader import load_manifest
from pipelines.acl import is_pipe_allowed

PIPE_URL = os.getenv("PIPE_URL", "http://localhost:8081")
PIPE_KEY = os.getenv("PIPE_KEY", "")


class EventEmitter:
    def __init__(self, emitter: Optional[Callable[[dict], Any]]) -> None:
        self._emitter = emitter

    async def emit(
        self,
        description: str,
        status: str = "in_progress",
        done: bool = False,
        progress: int | None = None,
    ) -> None:
        if self._emitter:
            await self._emitter(
                {
                    "type": "status",
                    "data": {
                        "status": status,
                        "description": description,
                        "done": done,
                        "progress": (
                            100 if done else 0 if progress is None else progress
                        ),
                    },
                }
            )


async def run_pipeline(
    pipe_id: str,
    metadata: dict[str, Any],
    user_prompt: str | None = None,
    *,
    __user__: dict | None = None,
    stream: bool = False,
    __event_emitter__: Callable[[dict], Any] | None = None,
) -> str:
    """Call external pipeline service and return JSON string."""
    emitter = EventEmitter(__event_emitter__)
    manifest = load_manifest()
    if not is_pipe_allowed(pipe_id, __user__, manifest):
        await emitter.emit("Pipeline not permitted", "error", True)
        return json.dumps({"error": {"code": "forbidden", "message": "Not allowed"}})

    await emitter.emit("Calling pipeline...")

    headers = {
        "Authorization": f"Bearer {PIPE_KEY}",
        "Content-Type": "application/json",
    }
    params = {"stream": "true" if stream else "false"}
    payload = {"pipe_id": pipe_id, "metadata": metadata, "user_prompt": user_prompt}

    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)
    ) as session:
        async with session.post(
            f"{PIPE_URL}/run",
            headers=headers,
            params=params,
            json=payload,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        ) as resp:
            if stream:
                async for line in resp.content:
                    if line.startswith(b"data:"):
                        try:
                            event = json.loads(line[5:].strip())
                        except Exception:
                            continue
                        if __event_emitter__:
                            await __event_emitter__(event)
                if 200 <= resp.status < 300:
                    await emitter.emit("Pipeline finished", "success", True)
                else:
                    await emitter.emit("Pipeline failed", "error", True)
                return ""

            data = await resp.json(content_type=None)
            if 200 <= resp.status < 300:
                await emitter.emit("Pipeline finished", "success", True)
            else:
                await emitter.emit("Pipeline failed", "error", True)
            return json.dumps(data, ensure_ascii=False)
