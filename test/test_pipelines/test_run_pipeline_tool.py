import asyncio
import json
import sys
import types

# Stub aiohttp and open_webui modules when running outside backend environment
if "aiohttp" not in sys.modules:
    aiohttp_stub = types.ModuleType("aiohttp")

    class _DummySession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

        def post(self, *args, **kwargs):
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

from tools import run_pipeline_tool


def test_streaming_large_response_not_truncated(monkeypatch):
    large_text = "x" * (1024 * 1024 + 5)
    sse_line = f"data: {json.dumps({'delta': {'content': large_text}})}\n\n".encode()

    class DummyContent:
        def __init__(self, lines):
            self._iter = iter(lines)

        def __aiter__(self):
            return self

        async def __anext__(self):
            try:
                return next(self._iter)
            except StopIteration:
                raise StopAsyncIteration

    class DummyResponse:
        def __init__(self, lines):
            self.content = DummyContent(lines)
            self.status = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

    class DummySession:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

        def post(self, *args, **kwargs):
            return DummyResponse([sse_line, b"data: [DONE]\n\n"])

    monkeypatch.setattr(run_pipeline_tool.aiohttp, "ClientSession", DummySession)
    monkeypatch.setattr(run_pipeline_tool.aiohttp, "ClientTimeout", lambda *a, **k: None)
    monkeypatch.setattr(run_pipeline_tool, "load_manifest", lambda: [{"id": "pipe", "group": "kb_admin"}])
    monkeypatch.setattr(run_pipeline_tool, "is_pipe_allowed", lambda pid, user, manifest: True)

    events = []

    async def emitter(event):
        events.append(event)

    result = asyncio.run(
        run_pipeline_tool.run_pipeline(
            "pipe",
            {},
            stream=True,
            __user__={"id": "1", "role": "admin"},
            __event_emitter__=emitter,
        )
    )

    assert result == ""
    streaming_events = [e for e in events if "delta" in e]
    assert streaming_events
    assert streaming_events[0]["delta"]["content"] == large_text
