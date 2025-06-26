# Standard library imports
import os
import json
from typing import Callable, Any, Optional

from pydantic import BaseModel

# Third party imports
import aiohttp

from open_webui.utils.auth import create_token
from open_webui.env import (
    AIOHTTP_CLIENT_TIMEOUT,
    AIOHTTP_CLIENT_SESSION_SSL,
)
from .decorators import deprecated

# Base URL of the Open WebUI API. This can be overridden with WEBUI_API_URL.
API_BASE_URL = os.getenv("WEBUI_API_URL", "http://localhost:8080")
# JWT used for authenticating against the API.
API_TOKEN = os.getenv("WEBUI_JWT", "")


class KnowledgeCreatePayload(BaseModel):
    """Payload for creating a knowledge entry."""

    name: str
    description: str


class FileIdPayload(BaseModel):
    """Payload containing a file ID."""

    file_id: str


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
        self.timeout = aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT)

    def _token_for_user(self, user: Optional[dict]) -> str:
        if self.token:
            return self.token
        user_id = (user or {}).get("id")
        if user_id:
            return create_token({"id": user_id})
        return ""

    def _headers(self, user: Optional[dict]) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        token = self._token_for_user(user)
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        json_body: BaseModel | dict | None = None,
        user: Optional[dict] = None,
    ) -> tuple[int, dict]:
        async with aiohttp.ClientSession(
            timeout=self.timeout, trust_env=True
        ) as session:
            try:
                if isinstance(json_body, BaseModel):
                    payload = json_body.model_dump(exclude_none=True)
                else:
                    payload = json_body
                async with session.request(
                    method,
                    f"{self.base_url}{endpoint}",
                    json=payload,
                    headers=self._headers(user),
                    ssl=AIOHTTP_CLIENT_SESSION_SSL,
                ) as resp:
                    text = await resp.text()
                    try:
                        data = json.loads(text) if text else {}
                    except Exception:
                        data = {"message": text}
                    return resp.status, data
            except Exception as exc:
                return 0, {"message": str(exc)}

    # -------- Knowledge endpoints --------
    async def create_knowledge(
        self,
        name: str,
        description: str,
        *,
        __user__: Optional[dict] = None,
        __event_emitter__: Optional[Callable[[dict], Any]] = None,
    ) -> str:
        emitter = EventEmitter(__event_emitter__)
        await emitter.emit("Creating knowledge entry...")
        payload = KnowledgeCreatePayload(name=name, description=description)
        status, data = await self._request(
            "POST",
            "/api/v1/knowledge/create",
            json_body=payload,
            user=__user__,
        )
        if status == 200:
            await emitter.emit("Knowledge created", "success", True)
        else:
            await emitter.emit("Failed to create knowledge", "error", True)
        return json.dumps(data, ensure_ascii=False)

    async def knowledge_list(
        self,
        *,
        __user__: Optional[dict] = None,
        __event_emitter__: Optional[Callable[[dict], Any]] = None,
    ) -> str:
        emitter = EventEmitter(__event_emitter__)
        await emitter.emit("Fetching knowledges...")
        status, data = await self._request(
            "GET",
            "/api/v1/knowledge/list",
            user=__user__,
        )
        if status == 200:
            await emitter.emit("Knowledge list retrieved", "success", True)
        else:
            await emitter.emit("Failed to fetch knowledges", "error", True)
        return json.dumps(data, ensure_ascii=False)

    async def get_knowledge_by_id(
        self,
        knowledge_id: str,
        *,
        __user__: Optional[dict] = None,
        __event_emitter__: Optional[Callable[[dict], Any]] = None,
    ) -> str:
        emitter = EventEmitter(__event_emitter__)
        await emitter.emit("Fetching knowledge...")
        status, data = await self._request(
            "GET",
            f"/api/v1/knowledge/{knowledge_id}",
            user=__user__,
        )
        if status == 200:
            await emitter.emit("Knowledge retrieved", "success", True)
        else:
            await emitter.emit("Knowledge not found", "error", True)
        return json.dumps(data, ensure_ascii=False)

    async def delete_knowledge(
        self,
        knowledge_id: str,
        *,
        __user__: Optional[dict] = None,
        __event_emitter__: Optional[Callable[[dict], Any]] = None,
    ) -> str:
        emitter = EventEmitter(__event_emitter__)
        await emitter.emit("Deleting knowledge...")
        status, data = await self._request(
            "DELETE",
            f"/api/v1/knowledge/{knowledge_id}/delete",
            user=__user__,
        )
        if status == 200:
            await emitter.emit("Knowledge deleted", "success", True)
        else:
            await emitter.emit("Deletion failed", "error", True)
        return json.dumps(data, ensure_ascii=False)

    # -------- File endpoints --------
    async def get_files_this_chat(
        self,
        *,
        __metadata__: Optional[dict] = None,
        __user__: Optional[dict] = None,
        __event_emitter__: Optional[Callable[[dict], Any]] = None,
    ) -> str:
        emitter = EventEmitter(__event_emitter__)
        chat_id = (__metadata__ or {}).get("chat_id")
        if not chat_id:
            await emitter.emit("Missing chat context", "error", True)
            return json.dumps({"message": "Missing chat context"})
        await emitter.emit("Fetching chat files...")
        url = "/api/v1/files/"
        status, data = await self._request("GET", url, user=__user__)
        if status == 200:
            files = data
            filtered = [f for f in files if f.get("meta", {}).get("chat_id") == chat_id]
            await emitter.emit(f"Found {len(filtered)} file(s)", "success", True)
            return json.dumps({"files": filtered}, ensure_ascii=False)
        await emitter.emit("Error contacting API", "error", True)
        return json.dumps(data, ensure_ascii=False)

    @deprecated
    async def get_files_from_knowledge(
        self,
        knowledge_id: str,
        *,
        __user__: Optional[dict] = None,
        __event_emitter__: Optional[Callable[[dict], Any]] = None,
    ) -> str:
        """List files attached to a Knowledge collection. Deprecated."""
        emitter = EventEmitter(__event_emitter__)
        await emitter.emit("Fetching knowledge files...")
        url = "/api/v1/files/"
        status, data = await self._request("GET", url, user=__user__)
        if status == 200:
            files = data
            filtered = [
                f
                for f in files
                if f.get("meta", {}).get("collection_name") == knowledge_id
            ]
            await emitter.emit(f"Found {len(filtered)} file(s)", "success", True)
            return json.dumps({"files": filtered}, ensure_ascii=False)
        await emitter.emit("Error contacting API", "error", True)
        return json.dumps(data, ensure_ascii=False)

    async def delete_file(
        self,
        file_id: str,
        *,
        __user__: Optional[dict] = None,
        __event_emitter__: Optional[Callable[[dict], Any]] = None,
    ) -> str:
        emitter = EventEmitter(__event_emitter__)
        await emitter.emit("Deleting file...")
        url = f"/api/v1/files/{file_id}"
        status, data = await self._request("DELETE", url, user=__user__)
        if status == 200:
            await emitter.emit("File deleted", "success", True)
        else:
            await emitter.emit("Deletion failed", "error", True)
        return json.dumps(data, ensure_ascii=False)

    async def add_file_to_knowledge(
        self,
        knowledge_id: str,
        file_id: str,
        *,
        __user__: Optional[dict] = None,
        __event_emitter__: Optional[Callable[[dict], Any]] = None,
    ) -> str:
        """Attach a file to the given knowledge base."""
        emitter = EventEmitter(__event_emitter__)
        await emitter.emit("Adding file to knowledge…")
        url = f"/api/v1/knowledge/{knowledge_id}/file/add"
        payload = FileIdPayload(file_id=file_id)
        status, data = await self._request(
            "POST",
            url,
            json_body=payload,
            user=__user__,
        )
        if status == 200:
            await emitter.emit("File added", "success", True)
        else:
            await emitter.emit("Failed to add file", "error", True)
        return json.dumps(data, ensure_ascii=False)

    async def remove_file_from_knowledge(
        self,
        knowledge_id: str,
        file_id: str,
        *,
        __user__: Optional[dict] = None,
        __event_emitter__: Optional[Callable[[dict], Any]] = None,
    ) -> str:
        """Detach a file from the given knowledge base."""
        emitter = EventEmitter(__event_emitter__)
        await emitter.emit("Removing file from knowledge…")
        url = f"/api/v1/knowledge/{knowledge_id}/file/remove"
        payload = FileIdPayload(file_id=file_id)
        status, data = await self._request(
            "POST",
            url,
            json_body=payload,
            user=__user__,
        )
        if status == 200:
            await emitter.emit("File removed", "success", True)
        else:
            await emitter.emit("Failed to remove file", "error", True)
        return json.dumps(data, ensure_ascii=False)
