This repository contains custom tooling under the `tools/` directory. When
modifying or extending these tools, always reference this file first.

Key points:
- New utilities live inside `tools/` without touching existing backend code.
- `knowledge_tool.py` and `files_tool.py` expose high level functions for
  managing Knowledges and Files via the Open WebUI models.
- Documentation of the work resides in `tools/prd.md`.

## Repository layout

- `backend/open_webui` – main FastAPI application with all models and routers.
- `src` – Svelte frontend sources.
- `tools` – helper modules used by AI agents.

## Coding style

- Format Python code with **Black**.
- Prefer asynchronous functions using `aiohttp` with the timeout and SSL
  settings from `open_webui.env`.
- Use `open_webui.utils.auth.create_token` to generate JWTs for the current user
  when calling the REST API from tools instead of hard coding tokens.
- Event emitters should follow the pattern used in existing tools, emitting
  dictionaries with `type` and `data` keys.
