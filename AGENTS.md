This repository contains custom tooling under the `tools/` directory. When
modifying or extending these tools, always reference this file first.

Key points:
- New utilities live inside `tools/` without touching existing backend code.
- `knowledge_tool.py` and `files_tool.py` expose high level functions for
  managing Knowledges and Files via the Open WebUI models.
- Documentation of the work resides in `tools/prd.md`.
