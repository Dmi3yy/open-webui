import asyncio
import json
import sys
import types

if "aiohttp" not in sys.modules:
    aiohttp_stub = types.ModuleType("aiohttp")

    class _DummySession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

        async def request(self, *args, **kwargs):
            raise RuntimeError("aiohttp stub: network disabled")

    aiohttp_stub.ClientTimeout = lambda *args, **kwargs: None
    aiohttp_stub.ClientSession = _DummySession
    sys.modules["aiohttp"] = aiohttp_stub

if "open_webui.utils.auth" not in sys.modules:
    auth_stub = types.ModuleType("open_webui.utils.auth")

    def _create_token(data):
        return "stub-token"

    auth_stub.create_token = _create_token

    package_stub = types.ModuleType("open_webui")
    utils_package = types.ModuleType("open_webui.utils")
    utils_package.auth = auth_stub
    package_stub.utils = utils_package
    sys.modules["open_webui"] = package_stub
    sys.modules["open_webui.utils"] = utils_package
    sys.modules["open_webui.utils.auth"] = auth_stub

if "open_webui.env" not in sys.modules:
    env_stub = types.ModuleType("open_webui.env")
    env_stub.AIOHTTP_CLIENT_TIMEOUT = None
    env_stub.AIOHTTP_CLIENT_SESSION_SSL = False
    utils_package.env = env_stub
    sys.modules["open_webui.env"] = env_stub

from pipelines import move_file_between_kb as pipe
from tools import openwebui_tool


def test_follow_up_when_missing():
    result = asyncio.run(pipe.run({}))
    assert result["finish_reason"] == "follow_up"
    assert set(result["follow_up"]["missing_fields"]) == {
        "src_kb_id",
        "dst_kb_id",
        "file_id",
    }


def test_success(monkeypatch):
    calls = []

    async def fake_add(self, kb_id, file_id, *, __user__=None, __event_emitter__=None):
        calls.append(("add", kb_id, file_id))
        return json.dumps({"ok": True})

    async def fake_remove(
        self, kb_id, file_id, *, __user__=None, __event_emitter__=None
    ):
        calls.append(("remove", kb_id, file_id))
        return json.dumps({"ok": True})

    monkeypatch.setattr(openwebui_tool.Tools, "add_file_to_knowledge", fake_add)
    monkeypatch.setattr(openwebui_tool.Tools, "remove_file_from_knowledge", fake_remove)

    metadata = {"src_kb_id": "a", "dst_kb_id": "b", "file_id": "c"}
    result = asyncio.run(pipe.run(metadata))
    assert result["finish_reason"] == "stop"
    assert result["content"]["moved"] is True
    assert calls == [("add", "b", "c"), ("remove", "a", "c")]
