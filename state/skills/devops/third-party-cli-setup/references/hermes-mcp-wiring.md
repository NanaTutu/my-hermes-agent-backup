# Wiring a third-party platform into Hermes via its MCP server

Session-verified (2026-08, Windows). Goal was: *"I want Hermes itself to call
Composio tools directly."* Result: `composio` MCP server registered in Hermes,
7 meta-tools discoverable, Gmail already connected upstream.

## The Composio surface (concrete facts)

- MCP endpoint: `https://connect.composio.dev/mcp` (Composio "Connect" server).
- It exposes **7 meta-tools**, not per-app tools — the agent orchestrates apps
  through these: `COMPOSIO_SEARCH_TOOLS`, `COMPOSIO_GET_TOOL_SCHEMAS`,
  `COMPOSIO_MULTI_EXECUTE_TOOL`, `COMPOSIO_MANAGE_CONNECTIONS`,
  `COMPOSIO_WAIT_FOR_CONNECTIONS`, `COMPOSIO_REMOTE_WORKBENCH`,
  `COMPOSIO_REMOTE_BASH_TOOL`. OAuth to upstream apps happens on-demand through
  these — the first time an app is used Composio emits an OAuth link.
- Auth: the dashboard (Settings → Sessions & API Key) documents
  `x-consumer-api-key: <key>`. A curl probe showed `Authorization: Bearer <key>`
  ALSO returns HTTP 200 — so Hermes's default Bearer template works.
- API key format: `ck_...`; created/managed in the dashboard. **Click Copy**
  there, then `powershell -NoProfile -Command "Get-Clipboard"` locally — never
  have the user paste the key into chat.

## Verify before wiring (the probe)

```bash
key="ck_..."
curl -s -w "\nHTTP %{http_code}\n" -X POST "https://connect.composio.dev/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer $key" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"probe","version":"1"}}}'
```

HTTP 200 with a `serverInfo` block = auth confirmed. A generic 401 body
("No Authorization: Bearer ... on request") is NOT proof Bearer is the required
scheme — the dashboard may document a different header; probe each candidate and
keep whichever returns 200.

## Attaching to Hermes (and the prompt workaround)

The ultrasonic interactive `hermes mcp add` password prompt is unreliable over
a non-TTY transport on Windows (piped stdin and background PTY both hang,
echoed input fuses with the prompt). Workaround — pre-seed the credential into
`.env` with Hermes's own helper, then let the CLI detect it:

```bash
cd "C:\Users\<user>\AppData\Local\hermes\hermes-agent"   # $HERMES_HOME/hermes-agent
python -c "from hermes_cli.config import save_env_value; save_env_value('MCP_COMPOSIO_API_KEY','ck_...')"

# then answer the remaining non-secret prompts via stdin:
printf 'Y\nY\n' | hermes mcp add composio --url "https://connect.composio.dev/mcp" --auth header --connect-timeout 90
```

Expected output:

```
✓ MCP_COMPOSIO_API_KEY: already configured
✓ Connected! Found 7 tool(s) from 'composio':
    COMPOSIO_SEARCH_TOOLS ...
    COMPOSIO_MANAGE_CONNECTIONS ...
    ...
Enable all 7 tools? [Y/n/select]:   ✓ Saved 'composio' to .../config.yaml (7/7 tools enabled)
```

Env key name follows `_env_key_for_server()`: server name upper-cased with
non-alphanumerics → `_`, suffix `_API_KEY` → `MCP_COMPOSIO_API_KEY`. Stored
config block (mask secrets):

```yaml
mcp_servers:
  composio:
    url: https://connect.composio.dev/mcp
    connect_timeout: 90.0
    headers:
      Authorization: Bearer ${MCP_COMPOSIO_API_KEY}
    enabled: true
```

Tools register as `mcp_composio_*`. Verify with `hermes mcp list`.

## Load timing — tell the user, don't surprise them

MCP tool discovery happens at agent startup. `hermes mcp add` prints
"Start a new session to use these tools." Tools will NOT appear in the live
session until `hermes gateway restart` (brief Telegram/network drop) then a new
session. Say this upfront so the user expects the absent tools.

## Environment notes (this machine)

- Hermes home = `C:\Users\bohen\AppData\Local\hermes` (`HERMES_HOME` unset);
  source at `.../hermes-agent/`.
- `hermes config set key val` is scalar-only — cannot write the nested
  `mcp_servers` dict; use `hermes mcp add` for MCP entries.
- MCP SDK dependency (`mcp` py package) already present with
  `streamable_http` support (checked via
  `python -c "from mcp.client.streamable_http import streamablehttp_client"`).