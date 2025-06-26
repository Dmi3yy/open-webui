import os
import json
import traceback
from datetime import datetime
from typing import Callable, Any

from pydantic import Field
from open_webui.models.files import Files, FileModel
from .decorators import deprecated

# Base address of the WebUI used to build links for returned files. This can
# be overridden with the `UI_BASE_URL` environment variable.
UI_BASE_URL = os.getenv("UI_BASE_URL", "http://localhost:8080")


class EventEmitter:
    """Emit status updates back to chat."""

    def __init__(self, emitter: Callable[[dict], Any] | None = None):
        self._emitter = emitter

    async def emit(
        self,
        description: str,
        status: str = "in_progress",
        done: bool = False,
        progress: int | None = None,
    ):
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


class Tools:
    """Expose file-related tools for the current user."""

    async def get_files_this_chat(
        self,
        *,
        __user__: dict | None = None,
        __metadata__: dict | None = None,
        __event_emitter__: Callable[[dict], Any] | None = None,
    ) -> str:
        """List files uploaded in the current chat."""
        emitter = EventEmitter(__event_emitter__)
        user_id = (__user__ or {}).get("id")
        chat_id = (__metadata__ or {}).get("chat_id")

        if not user_id or not chat_id:
            await emitter.emit("Missing user or chat context", "error", True)
            return json.dumps({"message": "Missing user or chat context"})

        await emitter.emit("Fetching chat files…")

        try:
            files = Files.get_files_by_chat_id(chat_id=chat_id, user_id=user_id)
            await emitter.emit(f"Found {len(files)} file(s)", "success", True)

            data = [
                {
                    "id": f.id,
                    "name": f.filename,
                    "size": f.size,
                    "created_at": datetime.utcfromtimestamp(f.created_at).isoformat(),
                    "link": f"{UI_BASE_URL}/workspace/file/{f.id}",
                }
                for f in files
            ]
            return json.dumps({"files": data}, ensure_ascii=False)
        except Exception as exc:
            await emitter.emit("Error retrieving files", "error", True)
            return json.dumps(
                {"message": str(exc), "trace": traceback.format_exc(limit=5)}
            )

    @deprecated
    async def get_files_from_knowledge(
        self,
        knowledge_id: str = Field(..., description="Knowledge collection ID."),
        *,
        __user__: dict | None = None,
        __event_emitter__: Callable[[dict], Any] | None = None,
    ) -> str:
        """List files attached to a Knowledge collection. Deprecated."""
        emitter = EventEmitter(__event_emitter__)
        user_id = (__user__ or {}).get("id")

        if not user_id:
            await emitter.emit("Missing user context", "error", True)
            return json.dumps({"message": "Missing user context"})

        await emitter.emit("Fetching knowledge files…")

        try:
            files = Files.get_files_by_knowledge_id(
                knowledge_id=knowledge_id, user_id=user_id
            )
            await emitter.emit(f"Found {len(files)} file(s)", "success", True)

            data = [
                {
                    "id": f.id,
                    "name": f.filename,
                    "size": f.size,
                    "created_at": datetime.utcfromtimestamp(f.created_at).isoformat(),
                    "link": f"{UI_BASE_URL}/workspace/file/{f.id}",
                }
                for f in files
            ]
            return json.dumps({"files": data}, ensure_ascii=False)
        except Exception as exc:
            await emitter.emit("Error retrieving files", "error", True)
            return json.dumps(
                {"message": str(exc), "trace": traceback.format_exc(limit=5)}
            )

    async def delete_file(
        self,
        file_id: str = Field(..., description="ID of the file to delete."),
        *,
        __user__: dict | None = None,
        __event_emitter__: Callable[[dict], Any] | None = None,
    ) -> str:
        """Delete a file owned by the current user."""
        emitter = EventEmitter(__event_emitter__)
        user_id = (__user__ or {}).get("id")

        if not user_id:
            await emitter.emit("Missing user context", "error", True)
            return json.dumps({"message": "Missing user context"})

        await emitter.emit("Verifying ownership…")

        try:
            file_obj: FileModel | None = Files.get_file_by_id(file_id)
            if not file_obj:
                await emitter.emit("File not found", "error", True)
                return json.dumps({"message": "File not found"})

            if file_obj.user_id != user_id:
                await emitter.emit("Access denied", "error", True)
                return json.dumps({"message": "Access denied"})

            if Files.delete_file_by_id(file_id):
                await emitter.emit("File deleted", "success", True)
                return json.dumps({"message": "File deleted", "id": file_id})

            await emitter.emit("Deletion failed", "error", True)
            return json.dumps({"message": "Deletion failed"})
        except Exception as exc:
            await emitter.emit("Error deleting file", "error", True)
            return json.dumps(
                {"message": str(exc), "trace": traceback.format_exc(limit=5)}
            )
