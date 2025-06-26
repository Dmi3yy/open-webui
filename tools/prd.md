# PRD — "Universal Pipeline Tool"
*Move / copy files between Knowledge Bases (KB) via Pipelines, invoked as a single Tool with streaming feedback*

---

## 1 · Problem Statement
Current workflow mixes **Tools** (synchronous, in‑process) and **Pipelines** (long‑running, external).
Users must manually switch the *Model selector* to a pipeline (`move_file_pipe`) or call several Tools in series. This is error‑prone and hides available pipelines.

---

## 2 · Goals
| ID | Goal |
|----|------|
| G‑1 | Expose **all permitted pipelines** through one Tool (`run_pipeline`) so LLM can function‑call them without model switching. |
| G‑2 | Replace bespoke multi‑step Tools (e.g. *moveFile*) with dedicated Pipelines; the Tool only proxies. |
| G‑3 | Support **interactive follow‑ups** (ask user for missing params) & **token streaming**. |
| G‑4 | Auto‑document available pipelines in the *system prompt* at launch, filtered by user permissions. |

---

## 3 · Solution Overview
```
User ──> LLM (function‑calling) ──> run_pipeline Tool
        │                                │
        │        SSE / JSON streaming    │
        └────────<────────<──────────────┘
                                    HTTP POST → /v1/chat/completions (Pipelines server)
```
* `run_pipeline` lives inside WebUI and:
  1. Discovers pipelines via `/pipelines/manifest.json` (lazy‑cached).
  2. Validates that `pipe_id` is in the allowed list for the user / group.
  3. Sends the OpenAI‑format request to `http://localhost:9099`.
  4. Streams partial tokens / follow‑up JSON back through `EventEmitter`.

* Each business flow (e.g. **MoveFile**) is now a pipeline:
  * `MoveFilePipe` handles steps 1‑6 (list KB, validate, transfer, verify).
  * If parameters are missing, it returns
    ```json
    {"type":"follow_up","missing_fields":["dst_kb_id"],"message":"Please specify…"}
    ```

* The LLM interprets `follow_up` and re‑calls `run_pipeline` with filled metadata.

---

## 4 · Detailed Requirements

### 4.1 `run_pipeline` Tool
| Requirement | Description |
|-------------|-------------|
| **Input** | `pipe_id:str`, `metadata:dict`, `user_prompt:str?` |
| **Transport** | HTTP POST → `PIPE_URL` (env) with Bearer `PIPE_KEY` |
| **Streaming** | If caller sets `stream=true`, proxy Server‑Sent Events chunk‑for‑chunk. |
| **Errors** | On non‑2xx, return `{ "error": {code, message} }` and status event “error”. |
| **Permissions** | `pipe_id` must be present in `allowed_pipelines` resolved for that user (see 4.3). |

### 4.2 Pipeline contract
| Field | Must |
|-------|------|
| `follow_up` | Provide list `missing_fields` + human `message`. |
| `content`   | For success: free‑form JSON or string. |
| `finish_reason` | `stop`, `follow_up`, or `error`. |
| Streaming | Optional `delta.content`. Tool proxies as‑is. |

### 4.3 Pipeline discovery & ACL
* **Manifest**: each pipeline registers itself into `/pipelines/manifest.json`:
  ```json
  {"id":"move_file_pipe","name":"Move File","group":"kb_admin","desc":""}
  ```
* **ACL Rules** (env var or DB table):
  `group → {user_ids, role_names}`
  Tool loads this once per request to filter manifest.

### 4.4 System‑Prompt Injection
* On boot, Tools module runs `load_manifest()` and creates a YAML snippet:
  ```
  ## Available Pipelines
  - id: move_file_pipe
    name: Move File between KBs
    call_via: run_pipeline
    required_metadata: [src_kb_id, dst_kb_id, file_id]
  ```
* The snippet is appended to the System prompt so the LLM “sees” callable pipelines.

---

## 5 · User Journeys

1. **Happy path**
   *User*: “Move file **123.pdf** from *Marketing‑2024* to *Conf‑2025*”
   ➜ LLM guesses IDs? if not → `follow_up` triggers “Which KBs exactly?” → user replies → pipeline executes → returns success JSON → LLM formats confirmation.

2. **Missing rights**
   Pipeline detects user not owner of destination KB → returns `error` → Tool surfaces status “Access denied”.

3. **Long copy** (>30 s)
   Pipeline streams progress tokens (`[#####.....] 50 %`) → Tool proxies → WebUI progress bubble animates.

### 5.1 Example cURL

Call the pipeline server directly using `run_pipeline` parameters:

```bash
curl -X POST "$PIPE_URL/run" \
  -H "Authorization: Bearer $PIPE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"pipe_id":"move_file_pipe","metadata":{"src_kb_id":"123","dst_kb_id":"456","file_id":"abc"}}'
```

---

## 6 · Non‑Goals
* Migrating **existing** small Tools (calculator, get_weather).
* UI buttons for pipelines — only LLM/function‑calling pathway.

---

## 7 · Sub‑Task Breakdown

| # | Title | Owner | Deliverable |
|---|-------|-------|-------------|
| **T‑1** | **Create manifest loader** | BE | `pipelines/loader.py` parses manifest, caches 60 s. |
| **T‑2** | **Role‑based ACL** | BE | `acl.py` util, ENV `PIPELINE_ACL_PATH`. |
| **T‑3** | **Refactor run_pipeline Tool** | BE | `tools/run_pipeline_tool.py` with SSE proxy, status events. |
| **T‑4** | **System‑prompt injector** | BE | Hook in `startup.py` appends YAML list. |
| **T‑5** | **MoveFilePipe implementation** | Pipelines | `pipelines/move_file_between_kb.py`, includes follow‑up logic, unit tests. |
| **T‑6** | **Streaming proxy tests** | QA | Ensure 1 MB+ responses stream without truncation. |
| **T‑7** | **Docs & examples** | DX | README: how to call `run_pipeline`, sample cURL. |
| **T‑8** | **Deprecate old tools** (`get_files_from_knowledge`, move logic) | BE | Mark with `@deprecated`, hide from spec. |

Deprecated tool functions should use ``tools.decorators.deprecated`` so they
are automatically excluded from the function spec.

---

## 8 · Acceptance Criteria
* Calling `run_pipeline` with full metadata moves a file in < 3 s 95‑percentile.
* When any required field is missing, user is asked exactly once per field.
* Streaming progress displays in WebUI without blocking UI.
* Pipeline list in system prompt matches `manifest.json` & ACL.
* Unit + integration tests green (`pytest -k pipelines`).

---

## 9 · Timeline (tentative)

| Week | Milestone |
|------|-----------|
| W +0 | T‑1, T‑2 complete |
| W +1 | T‑3, T‑4 merge; basic end‑to‑end happy path works |
| W +2 | T‑5, streaming QA (T‑6) |
| W +3 | Documentation, deprecation clean‑up |

---

## 10 · Open Questions
1. Should we support **batch move** (`file_ids:[]`) in v1?
2. Where to persist per‑user pipeline preference (e.g. hide advanced pipes)?
3. Do we need rollback if destination KB quota exceeded?
