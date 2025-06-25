import os
import json
from typing import Callable, Any, Optional

import aiohttp

# Base URL of the Open WebUI API. This can be overridden with WEBUI_API_URL.
API_BASE_URL = os.getenv("WEBUI_API_URL", "http://localhost:8080")
# JWT used for authenticating against the API.
API_TOKEN = os.getenv("WEBUI_JWT", "")


class EventEmitter:
    """Helper for emitting status updates back to the caller."""

    def __init__(self, emitter: Optional[Callable[[dict], Any]] = None) -> None:
        self._emitter = emitter

    async def emit(
        self,
        description: str,
        status: str = "in_progress",
        done: bool = False,
    ) -> None:
        if self._emitter:
            await self._emitter(
                {
                    "type": "status",
                    "data": {
                        "status": status,
                        "description": description,
                        "done": done,
                    },
                }
            )


class Tools:
    """Access a subset of the Open WebUI REST API."""

    def __init__(self, base_url: str | None = None, token: str | None = None) -> None:
        self.base_url = base_url or API_BASE_URL.rstrip("/")
        self.token = token or API_TOKEN

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    # -------- Knowledge endpoints --------
    async def create_knowledge(
        self,
        name: str,
        description: str,
        *,
        __event_emitter__: Optional[Callable[[dict], Any]] = None,
    ) -> str:
        emitter = EventEmitter(__event_emitter__)
        await emitter.emit("Creating knowledge entry...")
        url = f"{self.base_url}/api/v1/knowledge/create"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    url,
                    json={"name": name, "description": description},
                    headers=self._headers(),
                ) as resp:
                    data = await resp.json()
                    if resp.status == 200:
                        await emitter.emit("Knowledge created", "success", True)
                    else:
                        await emitter.emit("Failed to create knowledge", "error", True)
                    return json.dumps(data, ensure_ascii=False)
            except Exception as exc:
                await emitter.emit("Error contacting API", "error", True)
                return json.dumps({"message": str(exc)})

    async def knowledge_list(
        self,
        *,
        __event_emitter__: Optional[Callable[[dict], Any]] = None,
    ) -> str:
        emitter = EventEmitter(__event_emitter__)
        await emitter.emit("Fetching knowledges...")
        url = f"{self.base_url}/api/v1/knowledge/list"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=self._headers()) as resp:
                    data = await resp.json()
                    if resp.status == 200:
                        await emitter.emit("Knowledge list retrieved", "success", True)
                    else:
                        await emitter.emit("Failed to fetch knowledges", "error", True)
                    return json.dumps(data, ensure_ascii=False)
            except Exception as exc:
                await emitter.emit("Error contacting API", "error", True)
                return json.dumps({"message": str(exc)})

    async def get_knowledge_by_id(
        self,
        knowledge_id: str,
        *,
        __event_emitter__: Optional[Callable[[dict], Any]] = None,
    ) -> str:
        emitter = EventEmitter(__event_emitter__)
        await emitter.emit("Fetching knowledge...")
        url = f"{self.base_url}/api/v1/knowledge/{knowledge_id}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=self._headers()) as resp:
                    data = await resp.json()
                    if resp.status == 200:
                        await emitter.emit("Knowledge retrieved", "success", True)
                    else:
                        await emitter.emit("Knowledge not found", "error", True)
                    return json.dumps(data, ensure_ascii=False)
            except Exception as exc:
                await emitter.emit("Error contacting API", "error", True)
                return json.dumps({"message": str(exc)})

    async def delete_knowledge(
        self,
        knowledge_id: str,
        *,
        __event_emitter__: Optional[Callable[[dict], Any]] = None,
    ) -> str:
        emitter = EventEmitter(__event_emitter__)
        await emitter.emit("Deleting knowledge...")
        url = f"{self.base_url}/api/v1/knowledge/{knowledge_id}/delete"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.delete(url, headers=self._headers()) as resp:
                    text = await resp.text()
                    try:
                        data = json.loads(text)
                    except Exception:
                        data = {"message": text}
                    if resp.status == 200:
                        await emitter.emit("Knowledge deleted", "success", True)
                    else:
                        await emitter.emit("Deletion failed", "error", True)
                    return json.dumps(data, ensure_ascii=False)
            except Exception as exc:
                await emitter.emit("Error contacting API", "error", True)
                return json.dumps({"message": str(exc)})

    # -------- File endpoints --------
    async def get_files_this_chat(
        self,
        *,
        __metadata__: Optional[dict] = None,
        __event_emitter__: Optional[Callable[[dict], Any]] = None,
    ) -> str:
        emitter = EventEmitter(__event_emitter__)
        chat_id = (__metadata__ or {}).get("chat_id")
        if not chat_id:
            await emitter.emit("Missing chat context", "error", True)
            return json.dumps({"message": "Missing chat context"})
        await emitter.emit("Fetching chat files...")
        url = f"{self.base_url}/api/v1/files/"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=self._headers()) as resp:
                    files = await resp.json()
                    filtered = [
                        f for f in files if f.get("meta", {}).get("chat_id") == chat_id
                    ]
                    await emitter.emit(
                        f"Found {len(filtered)} file(s)", "success", True
                    )
                    return json.dumps({"files": filtered}, ensure_ascii=False)
            except Exception as exc:
                await emitter.emit("Error contacting API", "error", True)
                return json.dumps({"message": str(exc)})

    async def get_files_from_knowledge(
        self,
        knowledge_id: str,
        *,
        __event_emitter__: Optional[Callable[[dict], Any]] = None,
    ) -> str:
        emitter = EventEmitter(__event_emitter__)
        await emitter.emit("Fetching knowledge files...")
        url = f"{self.base_url}/api/v1/files/"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=self._headers()) as resp:
                    files = await resp.json()
                    filtered = [
                        f
                        for f in files
                        if f.get("meta", {}).get("collection_name") == knowledge_id
                    ]
                    await emitter.emit(
                        f"Found {len(filtered)} file(s)", "success", True
                    )
                    return json.dumps({"files": filtered}, ensure_ascii=False)
            except Exception as exc:
                await emitter.emit("Error contacting API", "error", True)
                return json.dumps({"message": str(exc)})

    async def delete_file(
        self,
        file_id: str,
        *,
        __event_emitter__: Optional[Callable[[dict], Any]] = None,
    ) -> str:
        emitter = EventEmitter(__event_emitter__)
        await emitter.emit("Deleting file...")
        url = f"{self.base_url}/api/v1/files/{file_id}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.delete(url, headers=self._headers()) as resp:
                    text = await resp.text()
                    try:
                        data = json.loads(text)
                    except Exception:
                        data = {"message": text}
                    if resp.status == 200:
                        await emitter.emit("File deleted", "success", True)
                    else:
                        await emitter.emit("Deletion failed", "error", True)
                    return json.dumps(data, ensure_ascii=False)
            except Exception as exc:
                await emitter.emit("Error contacting API", "error", True)
                return json.dumps({"message": str(exc)})
