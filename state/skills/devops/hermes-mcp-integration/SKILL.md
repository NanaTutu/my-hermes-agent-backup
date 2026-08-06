---
name: hermes-mcp-integration
description: Wire external MCP servers (Composio, GitHub) into Hermes.
---

# Hermes MCP Server Integration

Add remote MCP servers to Hermes so the **agent itself** calls external apps' tools (Composio, GitHub MCP, etc.). Hermes has first-class MCP support (`hermes mcp add`); no standalone SDK scripts needed.

## When to use
- User wants "Hermes itself" to call an external app's tools directly.
- An integration exposes a remote MCP endpoint (check vendor docs / dashboard).
- Prefer MCP over a vendor CLI when the CLI is unavailable on the platform — but let the user choose the path.

## Core workflow
1. **Probe the endpoint + auth before configuring.** Send a JSON-RPC `initialize` and read the HTTP code:
   ```
   curl -s -w "\nHTTP %{http_code}\n" -X POST <url> -H "Content-Type: application/json" \
     -H "Accept: application/json, text/event-stream" \
     -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"t","version":"1"}}}'
   ```
   - HTTP 200 → endpoint + header accepted. 401 → try alternative header forms (Bearer vs vendor-specific like `x-consumer-api-key`); vendors often accept several.
2. **Get the credential without transiting chat.** Vendor dashboards have a Sessions/API Keys page. Have the user (or drive the browser) click **Copy**, then read the clipboard locally: `powershell -NoProfile -Command "Get-Clipboard"`. Never paste the key into Telegram/chat; never write it into config.yaml.
3. **Store the key in Hermes `.env`** using Hermes' own helper (identical to what the CLI writes):
   ```
   python -c "from hermes_cli.config import save_env_value; save_env_value('MCP_<SERVER>_API_KEY','<key>')"
   ```
   (run from the hermes-agent dir so `hermes_cli` imports)
4. **Add the server:** `hermes mcp add <name> --url <url> --auth header`. Pre-setting the env var first makes the CLI print "MCP_...: already configured" and SKIP the flaky password prompt (see pitfalls).
5. **Verify:** `hermes mcp list` shows `✓ enabled`; grep config.yaml to confirm the header is the `${MCP_..._KEY}` placeholder, never the real key.
6. **Restart the gateway** — MCP tools load only at agent startup (CLI prints "Start a new session to use these tools" otherwise).

## Pitfalls
- **Never `hermes gateway restart` from inside the gateway.** It is blocked ("cannot restart or stop the gateway from inside the gateway process") — correct, it would SIGTERM itself. Use the detached watcher pattern below.
- **Interactive `hermes mcp add` prompts wedge over automation.** The `API key / Bearer token` prompt is `password=True` (no echo); piped stdin often never reaches it and the command hangs until timeout. Fix: pre-set the env var (step 3) and re-run — the prompt is skipped entirely.
- **Secret hygiene:** config.yaml headers must use `${MCP_..._KEY}` interpolation; the real credential lives only in `.env`. Before any backup push, confirm no real key leaked into config: `grep -c "<key-prefix>" config.yaml` → 0.
- **Windows schtasks needs single-slash flags** (`/Create`, `/Run`) — MSYS/git-bash `//Create` is an invalid-argument error.
- **Verify external dispatches landed before confirming to the user.** A claimed "sent" can silently never happen: if the agent's response is truncated mid-turn, the tool call after the truncation point never executes. Confirm via `GMAIL_LIST_THREADS` with `query: "in:sent to:<recipient>"` (or the send response's `labelIds:["SENT"]`) before telling the user it's sent. User rule (2026-08-06): "Next time double check if it is sent."
- Newly added MCP tools appear in a NEW session, not the current one.

## Restarting the gateway you're running inside (detached watcher)
The restart kills your session, so a watcher must survive it:
1. Write a PowerShell script: `Start-Sleep 12` (let the current turn flush its final message) → `hermes gateway restart` → poll `hermes gateway status` until output matches `Gateway process running` (new PID) → notify via `hermes send --to telegram "..."` (works without a running gateway).
2. Register + run as a Scheduled Task so it lives outside the gateway's process tree:
   ```
   schtasks /Create /TN <name> /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File <script>" /SC ONCE /ST 23:59 /F
   schtasks /Run /TN <name>
   ```
3. The "back online" notification comes from the watcher, not from the dead session. Expect a short silent gap — that is the restart.

## References
- `references/composio.md` — Composio-specific recipe: endpoint, auth forms, API-key flow, meta-tool execution protocol (SEARCH → GET_SCHEMAS → MULTI_EXECUTE), Gmail send verified end-to-end.
