# kennyken.top instance + verified local MCP scaffold

## Instance facts

- URL: `https://ragflow.kennyken.top/` — RAGFlow **v0.26.4** (confirmed via `GET /api/v1/system/version` → `{"code":0,"data":"v0.26.4"}`).
- Stack: Cloudflare → nginx → RAGFlow web/API server (9380 only).
- **Tutu has an account but does NOT control the server.** Cannot enable or proxy the MCP port (9382). This is why the local-bridge approach (SKILL.md "key trick") is the only "true MCP" path.

## Probe results (how "MCP not exposed" was confirmed)

- `POST /mcp` → `405 Not Allowed` (nginx) — streamable-HTTP endpoint not routed.
- `GET /sse` → returned the RAGFlow SPA `index.html`, not an SSE stream — fell through to web server.
- `GET /api/v1/system/version` → 200, no auth (public).
- `GET /api/v1/datasets`, `GET /api/v1/chats` → 401 (REST API live, needs Bearer key).

## Local scaffold (verified working)

Dir: `C:\Users\bohen\Documents\Hermes\ragflow-mcp\`

- `server.py` — official MCP server, downloaded from `https://raw.githubusercontent.com/infiniflow/ragflow/main/mcp/server/server.py` (924 lines, zero repo-internal imports).
- `.venv` — Python 3.11; deps `mcp>=1.28.1,<2.0.0 starlette httpx click uvicorn python-dotenv`.
- `.env.example` — template with the `RAGFLOW_MCP_*` vars; real `.env` is gitignored.
- `.gitignore` — `.env`, `.venv/`, `__pycache__/`.
- `run-server.ps1` — `Set-Location $PSScriptRoot; & ".\.venv\Scripts\python.exe" ".\server.py"` (config auto-loaded from `.env` via load_dotenv).

`.env` to create (API key goes in `RAGFLOW_MCP_HOST_API_KEY`, never in chat or scripts):

```
RAGFLOW_MCP_BASE_URL=https://ragflow.kennyken.top
RAGFLOW_MCP_HOST=127.0.0.1
RAGFLOW_MCP_PORT=9382
RAGFLOW_MCP_LAUNCH_MODE=self-host
RAGFLOW_MCP_HOST_API_KEY=
```

## mcp version pin journey

1. Initial `uv pip install mcp` resolved to `mcp==2.0.0` → `server.py` failed: `AttributeError: 'Server' object has no attribute 'list_tools'`.
2. Confirmed RAGFlow's `pyproject.toml` pins `mcp>=1.28.1,<2.0.0`.
3. `uv pip install "mcp>=1.28.1,<2.0.0"` → `mcp==1.29.0` → `server.py --help` imports clean.

## Remaining steps (resume point)

1. Get API key from RAGFlow UI (avatar → "API"), copy it; read from clipboard (PowerShell `Get-Clipboard`), write into `.env` (never chat/commit).
2. Launch: `run-server.ps1` (or run server.py directly); verify `POST http://127.0.0.1:9382/mcp` returns an MCP initialize response.
3. End-to-end check: call `ragflow_list_datasets` to confirm the key authorizes against the user's tenant.
4. `hermes mcp add ragflow --url http://127.0.0.1:9382/mcp` (no `--auth` in self-host) → restart gateway → new session.
5. Set up autostart at logon (scheduled task) so the local bridge stays up.
