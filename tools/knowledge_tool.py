import os
import json
import inspect
import traceback
from typing import Callable, Any
from datetime import datetime

# \u2714\ufe0f правильний імпорт для Open WebUI ≥ 0.6.x
from open_webui.models.knowledge import (
    Knowledges,
    KnowledgeForm,
    KnowledgeModel,
)

# Base address of the WebUI used for generating helpful links. It can be
# overridden with the `UI_BASE_URL` environment variable.
UI_BASE_URL = os.getenv("UI_BASE_URL", "http://localhost:8080")


class EventEmitter:
    def __init__(self, emitter: Callable[[dict], Any] | None = None):
        self._emitter = emitter

    async def emit(
        self,
        description: str,
        status: str = "in_progress",
        done: bool = False,
    ):
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
    # ---------- create_knowledge ----------
    async def create_knowledge(
        self,
        name: str,
        description: str,
        *,
        __user__: dict | None = None,
        __event_emitter__: Callable[[dict], Any] | None = None,
    ) -> str:
        """
        Створює новий об'єкт Knowledge і повертає JSON-опис.
        """
        emitter = EventEmitter(__event_emitter__)
        user_id = (__user__ or {}).get("id")
        if not user_id:
            await emitter.emit("Missing user context.", status="error", done=True)
            return json.dumps({"message": "Missing user context"})

        try:
            form = KnowledgeForm(name=name, description=description)
            entry: KnowledgeModel | None = Knowledges.insert_new_knowledge(
                user_id=user_id, form_data=form
            )
            if entry is None:
                raise RuntimeError("insert_new_knowledge returned None")
            await emitter.emit("Knowledge entry created.", status="success", done=True)
        except Exception as exc:
            err_msg = f"Failed to create knowledge entry: {exc}"
            await emitter.emit(err_msg, status="error", done=True)
            return json.dumps({"message": err_msg})

        link = f"{UI_BASE_URL}/workspace/knowledge/{entry.id}"
        return json.dumps(
            {
                "id": entry.id,
                "name": entry.name,
                "description": entry.description,
                "link": link,
            },
            ensure_ascii=False,
        )

    # ---------- knowledge_list ----------
    async def knowledge_list(
        self,
        *,
        __user__: dict | None = None,
        __event_emitter__: Callable[[dict], Any] | None = None,
    ) -> str:
        """
        Повертає список знань користувача з debug-інформацією.
        """
        emitter = EventEmitter(__event_emitter__)
        debug: dict[str, Any] = {}

        # Збираємо debug-інформацію про клас
        try:
            debug["module_file"] = inspect.getfile(Knowledges)
            debug["available_methods"] = [
                name
                for name in dir(Knowledges)
                if not name.startswith("__") and callable(getattr(Knowledges, name))
            ]
            await emitter.emit("Debug info collected", status="in_progress")
        except Exception as meta_exc:
            debug["meta_error"] = f"Introspection failed: {meta_exc}"

        # Перевірка наявності user_id
        user_id = (__user__ or {}).get("id")
        if not user_id:
            await emitter.emit("Missing user context.", status="error", done=True)
            return json.dumps({"message": "Missing user context", "debug": debug})

        # Отримуємо knowledge базах за правильним методом з джерел [2]
        try:
            # Використовуємо метод get_knowledge_bases_by_user_id з permission="read" для перегляду
            knowledge_bases = Knowledges.get_knowledge_bases_by_user_id(
                user_id=user_id, permission="read"
            )

            debug["found_count"] = len(knowledge_bases)
            await emitter.emit(
                f"Found {len(knowledge_bases)} knowledge entries.",
                status="success",
                done=True,
            )

        except Exception as exc:
            debug["fetch_error"] = {
                "type": type(exc).__name__,
                "msg": str(exc),
                "trace": traceback.format_exc(limit=5),
            }
            await emitter.emit(
                f"Failed to fetch knowledge entries: {exc}", status="error", done=True
            )
            return json.dumps(
                {"message": f"Fetch failed: {exc}", "debug": debug}, ensure_ascii=False
            )

        # Формуємо відповідь
        knowledges: list[dict[str, Any]] = []
        for kb in knowledge_bases:
            # knowledge_bases містить KnowledgeUserModel об'єкти
            created_iso = datetime.utcfromtimestamp(kb.created_at).isoformat()
            updated_iso = datetime.utcfromtimestamp(kb.updated_at).isoformat()

            knowledge_data = {
                "id": kb.id,
                "name": kb.name,
                "description": kb.description,
                "created_at": created_iso,
                "updated_at": updated_iso,
                "user_id": kb.user_id,
            }

            # Додаємо інформацію про користувача, якщо вона є
            if hasattr(kb, "user") and kb.user:
                knowledge_data["user"] = {
                    "name": kb.user.name,
                    "email": getattr(kb.user, "email", None),
                }

            # Додаємо link для UI
            knowledge_data["link"] = f"{UI_BASE_URL}/workspace/knowledge/{kb.id}"

            knowledges.append(knowledge_data)

        debug["processed_count"] = len(knowledges)

        result = {"knowledges": knowledges, "debug": debug, "status": "success"}

        return json.dumps(result, ensure_ascii=False)

    # ---------- get_knowledge_by_id ----------
    async def get_knowledge_by_id(
        self,
        knowledge_id: str,
        *,
        __user__: dict | None = None,
        __event_emitter__: Callable[[dict], Any] | None = None,
    ) -> str:
        """
        Отримує конкретний knowledge за ID.
        """
        emitter = EventEmitter(__event_emitter__)
        user_id = (__user__ or {}).get("id")

        if not user_id:
            await emitter.emit("Missing user context.", status="error", done=True)
            return json.dumps({"message": "Missing user context"})

        try:
            knowledge = Knowledges.get_knowledge_by_id(knowledge_id)

            if not knowledge:
                await emitter.emit("Knowledge not found.", status="error", done=True)
                return json.dumps({"message": "Knowledge not found"})

            await emitter.emit(
                "Knowledge retrieved successfully.", status="success", done=True
            )

            result = {
                "id": knowledge.id,
                "name": knowledge.name,
                "description": knowledge.description,
                "data": knowledge.data,
                "meta": knowledge.meta,
                "user_id": knowledge.user_id,
                "created_at": datetime.utcfromtimestamp(
                    knowledge.created_at
                ).isoformat(),
                "updated_at": datetime.utcfromtimestamp(
                    knowledge.updated_at
                ).isoformat(),
                "link": f"{UI_BASE_URL}/workspace/knowledge/{knowledge.id}",
            }

            return json.dumps(result, ensure_ascii=False)

        except Exception as exc:
            err_msg = f"Failed to get knowledge: {exc}"
            await emitter.emit(err_msg, status="error", done=True)
            return json.dumps({"message": err_msg, "trace": traceback.format_exc()})

    # ---------- delete_knowledge ----------
    async def delete_knowledge(
        self,
        knowledge_id: str,
        *,
        __user__: dict | None = None,
        __event_emitter__: Callable[[dict], Any] | None = None,
    ) -> str:
        """
        Видаляє кновледж за ID.
        """
        emitter = EventEmitter(__event_emitter__)
        user_id = (__user__ or {}).get("id")

        if not user_id:
            await emitter.emit("Missing user context.", status="error", done=True)
            return json.dumps({"message": "Missing user context"})

        try:
            # Перевіряємо, чи існує knowledge
            knowledge = Knowledges.get_knowledge_by_id(knowledge_id)
            if not knowledge:
                await emitter.emit("Knowledge not found.", status="error", done=True)
                return json.dumps({"message": "Knowledge not found"})

            # Перевіряємо права доступу (власник або має права на запис)
            if knowledge.user_id != user_id:
                await emitter.emit("Access denied.", status="error", done=True)
                return json.dumps({"message": "Access denied"})

            # Видаляємо
            success = Knowledges.delete_knowledge_by_id(knowledge_id)

            if success:
                await emitter.emit(
                    "Knowledge deleted successfully.", status="success", done=True
                )
                return json.dumps(
                    {"message": "Knowledge deleted successfully", "id": knowledge_id}
                )
            else:
                await emitter.emit(
                    "Failed to delete knowledge.", status="error", done=True
                )
                return json.dumps({"message": "Failed to delete knowledge"})

        except Exception as exc:
            err_msg = f"Failed to delete knowledge: {exc}"
            await emitter.emit(err_msg, status="error", done=True)
            return json.dumps({"message": err_msg, "trace": traceback.format_exc()})
