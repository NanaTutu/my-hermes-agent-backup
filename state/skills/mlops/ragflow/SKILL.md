---
name: ragflow
description: Use when connecting to or integrating RAGFlow (REST or MCP).
---

# RAGFlow integration

RAGFlow is an open-source RAG engine. It exposes a REST API and an optional MCP server. This skill covers the architecture, the REST API, and — most importantly — how to get genuine MCP access even when you only hold an account on someone else's hosted instance.

## Architecture (facts)

- Web UI + REST API server listen on port **9380**. Base API path: `/api/v1`.
- The MCP server is a **separate process on port 9382**. It is NOT served by the web server. Enabling/proxying 9380 does NOT expose MCP.
- REST auth: `Authorization: Bearer <api_key>` on every request. Keys start with `ragflow-`.
- `GET /api/v1/system/version` is public (no auth) — a fast health/version probe.
- Auth-required endpoints (e.g. `/api/v1/datasets`, `/api/v1/chats`) return 401 without a key.

## MCP server (official, RAGFlow v0.18.0+)

Repo `infiniflow/ragflow`, path `mcp/server/server.py`. It is a thin wrapper over the public REST API — its connector only calls `{base_url}/api/v1/datasets`, `/api/v1/chats`, and `/api/v1/retrieval` with Bearer auth. It exposes exactly 3 tools:

- `ragflow_retrieval` — retrieve ranked chunks for a question (POST `/api/v1/retrieval`)
- `ragflow_list_datasets` — list knowledge bases (id, name, description)
- `ragflow_list_chats` — list chat assistants

Transports: streamable HTTP at `/mcp`, legacy SSE at `/sse` (both on by default). Two launch modes:

- **self-host** (default): the server holds one API key; the MCP client connects with NO auth. Exposes that one tenant's datasets.
- **host**: each client request must carry its own API-key/Bearer header.

### Key trick — MCP access when you do NOT control the instance

Because the MCP server only needs the public REST API, run it **locally** and point it at the remote instance:

```
python server.py --host=127.0.0.1 --port=9382 \
  --base-url=https://<remote-host> \
  --api-key=<your-account-api-key>   # self-host mode
```

This is real MCP with zero server-side changes, fully under your control. You never need the owner to expose port 9382.

### Diagnosis — is MCP actually exposed on a domain?

- A real MCP server answers `POST <host>/mcp` with an MCP JSON-RPC response.
- If `POST <host>/mcp` returns **405 Not Allowed** (nginx), or `GET <host>/sse` returns the web UI's `index.html` (SPA fallback) instead of an SSE stream → the reverse proxy only routes 9380; MCP (9382) is NOT exposed.

### Config — env vars (server.py reads these after `load_dotenv()`)

- `RAGFLOW_MCP_BASE_URL`, `RAGFLOW_MCP_HOST`, `RAGFLOW_MCP_PORT`, `RAGFLOW_MCP_LAUNCH_MODE` (`self-host`|`host`), `RAGFLOW_MCP_HOST_API_KEY`, plus `_TRANSPORT_SSE_ENABLED` / `_TRANSPORT_STREAMABLE_ENABLED` / `_JSON_RESPONSE` toggles.
- `load_dotenv()` reads a `.env` from the CWD — so put the API key in a local `.env` (gitignored) and `cd` into the dir before launching. This keeps the key out of the command line AND out of any committed script.

## Version pin (critical pitfall)

- RAGFlow's `pyproject.toml` pins `mcp>=1.28.1,<2.0.0`.
- `mcp 2.0.0` removed the lowlevel Server API → `server.py` crashes at import: `'Server' object has no attribute 'list_tools'`.
- Fix: `uv pip install "mcp>=1.28.1,<2.0.0"` (resolves to 1.29.0; imports clean).
- `server.py` also uses `from enum import StrEnum` → needs Python 3.11+.
- Leftover `mcp-types`/`httpcore2`/`httpx2` packages from a stray mcp 2.0 install are harmless after downgrading.

## Wiring into Hermes

```
hermes mcp add ragflow --url http://127.0.0.1:9382/mcp     # NO --auth in self-host mode
hermes mcp list                                           # confirm ✓ enabled + tool count
```

- Restart the gateway; the 3 tools load in a NEW session, not the current one.
- Hermes `--url` handles HTTP/SSE MCP endpoints (see `hermes-mcp-integration` skill for the full secret-hygiene workflow: clipboard-read the key, `save_env_value`, never paste into chat).

## REST API quick reference (direct use, no MCP)

- `GET /api/v1/datasets`, `GET /api/v1/chats` — list (Bearer auth)
- `POST /api/v1/retrieval` — `{question, dataset_ids[], document_ids[], similarity_threshold, vector_similarity_weight, top_k, keyword, page, page_size}`
- `GET /api/v1/datasets/{id}/documents?page=&page_size=` — list documents
- `GET /api/v1/datasets/{id}/documents/{doc_id}/chunks?page=&page_size=` — list a document's chunks. **page_size max is 100** (128 returns `code:100`; 1024 returns `data:null`). Paginate 100/page over `data.total`.
- API key location: RAGFlow UI → avatar (top-right) → "API" / "API Key"

## Pitfalls

- Exposing the MCP server publicly in self-host mode is effectively unauthenticated (server-side key, not per-request). RAGFlow docs say bind 127.0.0.1. Running the local bridge (key trick above) sidesteps this entirely.
- Reverse-proxying the RAGFlow UI does not make MCP reachable — they are different ports (9380 vs 9382).
- The chunks-listing endpoint returns content with the parent heading PREPENDED (e.g. `CHAPTER I — THE CONSTITUTION\nArticle 1\n1. SUPREMACY...`), while `/api/v1/retrieval` returns content starting at the article. So "Article N" is often NOT the first line of a listed chunk — match it with a multiline regex (`^Article\s+(\d+)$`), not `content.split("\n")[0]`.

## References

- `references/kennyken-instance.md` — the hosted instance this was first set up against, exact probe results, and the verified local MCP scaffold.
