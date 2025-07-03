import copy
import json
import os
import re
import time
from typing import Any, Awaitable, Callable, Optional

import aiohttp
from pydantic import BaseModel, Field

from open_webui.utils.auth import create_token
from open_webui.env import AIOHTTP_CLIENT_TIMEOUT, AIOHTTP_CLIENT_SESSION_SSL


def extract_event_info(
    event_emitter: Optional[Callable[..., Any]],
) -> tuple[Optional[str], Optional[str]]:
    """Pull chat and message identifiers from the event emitter closure."""
    if not event_emitter or not getattr(event_emitter, "__closure__", None):
        return None, None
    for cell in event_emitter.__closure__:
        request_info = cell.cell_contents
        if isinstance(request_info, dict):
            return request_info.get("chat_id"), request_info.get("message_id")
    return None, None


class Pipe:
    """Bridge OpenWebUI chat data to an n8n workflow."""

    class Valves(BaseModel):
        n8n_url: str = Field(
            default="https://n8n.[your domain].com/webhook/[your webhook]"
        )
        n8n_bearer_token: str = Field(default="...")
        openwebui_api_url: str = Field(default="http://localhost:8080/api/v1/files")
        openwebui_api_token: Optional[str] = Field(default=None)
        input_field: str = Field(default="chatInput")
        response_field: str = Field(default="output")
        emit_interval: float = Field(default=2.0)
        enable_status_indicator: bool = Field(default=True)

    def __init__(self) -> None:
        self.type = "pipe"
        self.id = "n8n_pipe"
        self.name = "N8N Pipe"
        self.valves = self.Valves()
        self.last_emit_time = 0.0
        self.debug = bool(os.getenv("N8N_PIPE_DEBUG"))

    async def emit_status(
        self,
        __event_emitter__: Optional[Callable[[dict], Awaitable[None]]],
        level: str,
        message: str,
        done: bool = False,
    ) -> None:
        """Send a status message back to the chat UI."""
        if not __event_emitter__:
            return
        now = time.time()
        if self.valves.enable_status_indicator and (
            now - self.last_emit_time >= self.valves.emit_interval or done
        ):
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "status": "complete" if done else "in_progress",
                        "level": level,
                        "description": message,
                        "done": done,
                    },
                }
            )
            self.last_emit_time = now

    async def get_files_for_session(
        self, session_id: str, user: Optional[dict]
    ) -> list:
        """Retrieve files for the current chat session via the REST API."""
        params = {"session_id": session_id}
        headers: dict[str, str] = {}
        token = self.valves.openwebui_api_token
        if not token and user and user.get("id"):
            # Generate JWT for the current user if token not provided
            token = create_token({"id": user["id"]})
        if token:
            headers["Authorization"] = f"Bearer {token}"
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)
        ) as session:
            async with session.get(
                self.valves.openwebui_api_url,
                params=params,
                headers=headers,
                ssl=AIOHTTP_CLIENT_SESSION_SSL,
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
        return sorted(data, key=lambda x: x.get("created_at", 0))

    async def pipe(
        self,
        body: dict,
        __user__: Optional[dict] = None,
        __event_emitter__: Optional[Callable[[dict], Awaitable[None]]] = None,
        __event_call__: Optional[Callable[[dict], Awaitable[dict]]] = None,
    ) -> Optional[dict]:
        """Main entry point used by the tool server."""

        await self.emit_status(__event_emitter__, "info", "Calling n8n Agent…", False)
        chat_id, _ = extract_event_info(__event_emitter__)
        # NOTE: session_id used in socket handlers is not the same as chat_id.
        messages = body.get("messages", [])
        if not messages:
            await self.emit_status(__event_emitter__, "error", "No messages", True)
            return {"error": "No messages found"}
        question = messages[-1].get("content", "")

        payload = copy.deepcopy(body)
        payload["sessionId"] = str(chat_id)
        payload[self.valves.input_field] = question

        files = (
            await self.get_files_for_session(payload["sessionId"], __user__)
            if payload.get("sessionId")
            else []
        )
        files_grouped: dict[str, list] = {}
        for f in files:
            fname = f.get("name") or f.get("filename") or f.get("file_name")
            files_grouped.setdefault(fname, []).append(f)

        system_msg = next(
            (m for m in payload.get("messages", []) if m.get("role") == "system"), None
        )
        sources = []
        if system_msg and "<source" in system_msg.get("content", ""):
            pattern = r'<source\s+id="(?P<id>[^"]+)"\s+name="(?P<name>[^"]+)">(?P<content>.*?)</source>'
            raw_sources = [
                m.groupdict()
                for m in re.finditer(pattern, system_msg["content"], flags=re.S)
            ]
            name_counters: dict[str, int] = {}
            for s in raw_sources:
                name = s["name"]
                idx = name_counters.get(name, 0)
                file_id = None
                file_list = files_grouped.get(name)
                if file_list and idx < len(file_list):
                    file_id = file_list[idx].get("id")
                name_counters[name] = idx + 1
                s["file_id"] = file_id
                sources.append(s)
        if sources:
            payload["sources"] = sources

        payload["debug_dump"] = json.dumps(payload, ensure_ascii=False, indent=2)

        if self.debug:
            print("--- N8N_PIPE DEBUG FULL PAYLOAD ---")
            print(payload["debug_dump"])
            print("--- END DEBUG ---")
            await self.emit_status(
                __event_emitter__, "debug", "FULL PAYLOAD attached", False
            )

        headers = {
            "Authorization": f"Bearer {self.valves.n8n_bearer_token}",
            "Content-Type": "application/json",
        }
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)
            ) as session:
                async with session.post(
                    self.valves.n8n_url,
                    json=payload,
                    headers=headers,
                    ssl=AIOHTTP_CLIENT_SESSION_SSL,
                ) as resp:
                    resp.raise_for_status()
                    data = await resp.json(content_type=None)
                    reply = (
                        data.get(self.valves.response_field)
                        if isinstance(data, dict)
                        else None
                    )
        except Exception as exc:
            await self.emit_status(__event_emitter__, "error", str(exc), True)
            return {"error": str(exc)}

        body.setdefault("messages", []).append({"role": "assistant", "content": reply})

        await self.emit_status(__event_emitter__, "info", "Complete", True)
        return reply
