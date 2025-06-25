# Open WebUI Custom Tools PRD

This project adds a new `tools` package that exposes helper utilities for
managing Knowledges and Files inside Open WebUI via AI agents.

## Features

1. **Knowledge Tool (`knowledge_tool.py`)**
   - Create, list, fetch and delete knowledge bases.
   - Emits progress updates using an optional event emitter.
   - Returns JSON responses containing links to the Web UI for quick access.

2. **Files Tool (`files_tool.py`)**
   - List files for the current chat or a specific knowledge base.
   - Delete files if the current user owns them.

3. **OpenWebUI API Tool (`openwebui_tool.py`)**
   - Communicates with the Open WebUI REST API using an authentication token.
   - Offers the same operations as the above tools but via HTTP requests.

Both tools rely on the existing `open_webui` Python package and mirror the
behaviour of the API endpoints. They are designed to be called from chat based
workflows with the following environment variables:

- `UI_BASE_URL` – Base URL of the Web UI (defaults to `http://localhost:8080`).
- `WEBUI_API_URL` – Base URL of the API (defaults to `http://localhost:8080`).
- `WEBUI_JWT` – JWT token used for authentication with the API.

## Usage Overview

1. Copy the tools into the project under the `tools/` directory.
2. Import the `Tools` class from either module and call the desired coroutine.
3. Supply user context and an optional async event emitter to receive status
   updates.
4. Parse the JSON result for information about created or fetched resources.

Future iterations will extend these tools with more robust error handling and
additional functionality such as moving files between knowledges or uploading
chat files directly into a knowledge base.
