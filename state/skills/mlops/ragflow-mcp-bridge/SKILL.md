---
name: ragflow-mcp-bridge
description: Use for RAGFlow — local MCP bridge to ragflow.kennyken.top.
---

# RAGFlow MCP Bridge (local)

Tutu has an ACCOUNT on a hosted RAGFlow instance (https://ragflow.kennyken.top, v0.26.4) but does NOT control the server. The instance's own MCP endpoint (port 9382) is therefore NOT exposed through the domain — `/mcp` returns 405, `/sse` falls through to the SPA. The official RAGFlow MCP server is a thin wrapper over the public REST API, so the fix is to run it LOCALLY, pointed at the remote instance with Tutu's account API key. This is genuine MCP with zero server-side changes.

## Architecture
Hermes --(MCP streamable HTTP)--> local server.py @ 127.0.0.1:9382 --(Bearer key)--> https://ragflow.kennyken.top/api/v1

The official server's RAGFlowConnector only calls `/api/v1/datasets`, `/api/v1/chats`, `/api/v1/retrieval` with `Authorization: Bearer <key>` — nothing internal, so it works against any reachable RAGFlow REST API.

## Locations
- Project: `C:\Users\bohen\Documents\Hermes\ragflow-mcp\`
  - `server.py` — official MCP server (from infiniflow/ragflow `mcp/server/server.py`, ~924 lines, no repo-internal imports)
  - `.env` — gitignored; holds config + `RAGFLOW_MCP_HOST_API_KEY`
  - `.env.example` — template
  - `run-server.ps1` — supervisor loop (restarts server on exit)
  - `ragflow-mcp-autostart.vbs` — non-admin logon autostart, hidden window
  - `.venv` — Python 3.11 + deps
- Hermes: MCP server `ragflow` → `http://127.0.0.1:9382/mcp` (config.yaml, no auth, no secret)

## Tools exposed (4)
`ragflow_retrieval`, `ragflow_list_datasets`, `ragflow_list_chats`, `ragflow_get_article`

`ragflow_get_article(article_number[, dataset_id])` is a LOCAL PATCH — upstream ships only 3 tools. It solves the exact-article-number lookup problem: semantic retrieval fails on bare numbers (querying "Article 10" returns unrelated articles 19/179/69). The tool walks the document chunks and matches the chunk whose content starts with "Article <N>" (guarded against "Article 10" matching "Article 100"), paging via the chunks REST endpoint. Works for any article number.

## Local fork note
`server.py` is forked from upstream (3 patches: `RAGFlowConnector.get_article` + `_list_documents` methods, a 4th `types.Tool` in `list_tools`, and a `ragflow_get_article` branch in `call_tool`). If you re-download upstream `server.py`, re-apply these — diff is small and self-contained (uses only `_get`, `resolve_dataset_ids`, `_REST_API_MAX_PAGE_SIZE`; no new imports).

## Full setup
1. **Deps** (pin mcp <2.0 — see pitfall):
   ```
   uv venv --python 3.11 .venv
   uv pip install --python .venv/Scripts/python.exe "mcp>=1.28.1,<2.0.0" starlette httpx click uvicorn python-dotenv
   ```
2. **Download** `server.py` from `https://raw.githubusercontent.com/infiniflow/ragflow/main/mcp/server/server.py`
3. **`.env`** (self-host mode — the server itself holds the key, client needs no auth):
   ```
   RAGFLOW_MCP_BASE_URL=https://ragflow.kennyken.top
   RAGFLOW_MCP_HOST=127.0.0.1
   RAGFLOW_MCP_PORT=9382
   RAGFLOW_MCP_LAUNCH_MODE=self-host
   RAGFLOW_MCP_HOST_API_KEY=ragflow-xxxx
   ```
   The server reads these via `load_dotenv()` + `os.environ`, so the key never sits on a command line or in a script.
4. **Launch**: `run-server.ps1` (Set-Location to script dir, then runs `.venv\Scripts\python.exe server.py` in a `while($true)` supervisor loop).
5. **Verify** the handshake:
   ```
   curl -s -X POST http://127.0.0.1:9382/mcp -H "Content-Type: application/json" \
     -H "Accept: application/json, text/event-stream" \
     -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"probe","version":"1"}}}'
   ```
   Expect `serverInfo.name == "ragflow-mcp-server"`. Also test `tools/call` with `ragflow_list_datasets` for a real end-to-end data check.
6. **Wire Hermes** (pipe the answers — see pitfalls):
   ```
   printf 'n\nY\nY\n' | hermes mcp add ragflow --url http://127.0.0.1:9382/mcp
   ```
7. **Autostart (non-admin)**: scheduled tasks need ELEVATION (`Register-ScheduledTask`/`schtasks /Create` → Access denied). Use the Startup-folder VBS instead — `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\ragflow-mcp-autostart.vbs` runs `run-server.ps1` hidden (`WScript.Shell.Run ..., 0, False`). Launch now: `wscript.exe //B "C:\Users\bohen\Documents\Hermes\ragflow-mcp\ragflow-mcp-autostart.vbs"`.
8. **New session** to load the 3 tools (CLI prints "Start a new session to use these tools").

## Pitfalls
- **`mcp==2.0.0` breaks the official server** — `AttributeError: 'Server' object has no attribute 'list_tools'`. RAGFlow pins `mcp>=1.28.1,<2.0.0`; install 1.29.x. Verify with `server.py --help`.
- **`hermes mcp add` auth prompt**: it asks "Does this server require authentication? [Y/n]". Answer **`n`** — in self-host mode there is NO client auth (the server holds the key). Answering `Y` leads to a hidden `password=True` prompt that wedges over piped stdin.
- **schtasks/Register-ScheduledTask need elevation** on this box (non-admin shell → Access denied). Use the Startup-folder VBS, not a scheduled task.
- **Port already in use** when re-launching: kill the previous wscript/python first, or the new server fails to bind 9382.

## Key handling
- API key lives ONLY in `Documents\Hermes\ragflow-mcp\.env` (gitignored). Never in config.yaml (this server needs no Hermes-side secret), never in scripts, never pasted in chat — prefer reading the user's clipboard.

## Troubleshooting
- Port closed → relaunch the VBS; check with `(echo >/dev/tcp/127.0.0.1/9382)`.
- Import errors → confirm `mcp` is 1.x.
- REST 401 → key invalid/rotated: get a new key (ragflow.kennyken.top → avatar → API), update `.env`, restart the server.
