# Repository Map

This document provides a high-level overview of the main directories in this project to help you locate code quickly.

## Top level

- **backend/** – backend services and application code.
- **src/** – Svelte frontend sources.
- **tools/** – helper modules used by AI agents.
- **docs/** – documentation files.
- **kubernetes/** – deployment manifests and Helm chart.
- **cypress/** – end-to-end test specifications.
- **static/** – public static assets served by the frontend.
- **scripts/** – small maintenance and build scripts.
- other root files such as Dockerfiles, configuration and package manifests.

## backend

`backend/` contains the Python FastAPI application located under `backend/open_webui`:

- **open_webui/main.py** – FastAPI entrypoint.
- **routers/** – API route definitions.
- **models/** – database models and schemas.
- **utils/** – shared utilities.
- **migrations/** – Alembic migration scripts.
- **storage/** and **data/** – persisted files and default data.
- **tasks.py** and **socket/** – background tasks and websocket logic.

## tools

Utilities for agents live under `tools/`:

- **knowledge_tool.py** – manage Knowledges.
- **files_tool.py** – operate on uploaded files.
- **openwebui_tool.py** – wrappers around the REST API.
- **prd.md** – design document describing these tools.

## frontend

`src/` contains the Svelte application with `routes/` for pages and `lib/` for components, APIs and stores.

Use this map as a quick reference when browsing the codebase.
