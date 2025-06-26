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

## Current Tasks

The `tools/prd.md` document describes the **Universal Pipeline Tool**. Agents working in this repository should focus on the following tasks:

- **T-1**: Create the manifest loader in `pipelines/loader.py` that caches entries for 60 seconds.
- **T-2**: Implement role-based ACL using `acl.py` and the `PIPELINE_ACL_PATH` environment variable.
- **T-3**: Refactor the `run_pipeline` tool with SSE proxying and status events.
- **T-4**: Inject available pipelines into the system prompt during startup.
- **T-5**: Implement `MoveFilePipe` with follow-up logic and unit tests.
- **T-6**: Add streaming proxy tests ensuring large responses are not truncated.
- **T-7**: Update documentation with usage examples for `run_pipeline`.
- **T-8**: Deprecate old tools such as `get_files_from_knowledge`.

Refer to the PRD for detailed requirements.
