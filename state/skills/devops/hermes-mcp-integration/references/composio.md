# Composio via Hermes MCP (verified end-to-end 2026-08-06)

## Endpoint & auth
- Remote MCP endpoint: `https://connect.composio.dev/mcp`
- Auth: `Authorization: Bearer <API_KEY>` AND `x-consumer-api-key: <API_KEY>` both return HTTP 200 on the `initialize` probe (key format `ck_...`).
- Key source: Composio dashboard (signed-in workspace) → **Settings → Sessions & API Key**. Key is masked in UI (`ck_BHK•••CSsp`); use the **Copy** button then `powershell -NoProfile -Command "Get-Clipboard"` — key never transites chat.
- CLI caveat (why MCP path was chosen): Composio CLI is Linux/macOS-only; npm package `composio` is an unrelated 2020 UI-components decoy. Not needed with the MCP route.

## Hermes-side wiring
```
python -c "from hermes_cli.config import save_env_value; save_env_value('MCP_COMPOSIO_API_KEY','<key>')"   # from hermes-agent dir
hermes mcp add composio --url "https://connect.composio.dev/mcp" --auth header
```
- Env var must be pre-set so the CLI skips its (automation-hostile) password prompt.
- Resulting config.yaml:
  ```yaml
  mcp_servers:
    composio:
      url: https://connect.composio.dev/mcp
      connect_timeout: 90.0
      headers:
        Authorization: Bearer ${MCP_COMPOSIO_API_KEY}
      enabled: true
  ```
- Discovers 7 meta-tools (prefixed `mcp_composio_*` in Hermes): COMPOSIO_SEARCH_TOOLS, COMPOSIO_GET_TOOL_SCHEMAS, COMPOSIO_MULTI_EXECUTE_TOOL, COMPOSIO_MANAGE_CONNECTIONS, COMPOSIO_WAIT_FOR_CONNECTIONS, COMPOSIO_REMOTE_BASH_TOOL, COMPOSIO_REMOTE_WORKBENCH.
- Verify with `hermes mcp list` (shows `composio ✓ enabled`); then restart gateway + new session for the tools to load.

## Execution protocol (how to actually call an app via Composio)
Follow strictly — each meta-tool has purpose:
1. **COMPOSIO_SEARCH_TOOLS** — first call for any workflow. Arguments: `queries:[{use_case, known_fields}]`, `session:{generate_id:true}`. Returns recommended plan + pitfalls, tool slugs, `toolkit_connection_statuses` (must be ACTIVE), and a `session.id` (e.g. "page") to reuse in all subsequent calls. Check connection is active before executing; if not, use COMPOSIO_MANAGE_CONNECTIONS first.
2. **COMPOSIO_GET_TOOL_SCHEMAS** — load full input schema for any tool that came back with `schemaRef` instead of inline `input_schema`. Never invent slugs; only pass slugs the search returned.
3. **COMPOSIO_MULTI_EXECUTE_TOOL** — execute with `tools:[{tool_slug, arguments}]`, plus `session_id` from search, `thought`, `current_step`, `sync_response_to_workbench` (false for small payloads). Up to 50 independent tools in parallel; batch only logically independent calls.

### GMAIL_SEND_EMAIL (verified, 2 sends)
Required args seen in schema: `recipient_email` (full user@domain string), at least one of `subject`/`body`, `is_html` only if HTML body. Optional `cc`, `bcc`, `extra_recipients`, `attachment`. Sends immediately (irreversible). Response: `{successful:true, data:{id, threadId, labelIds:["SENT"], display_url}}`; message link = `https://mail.google.com/mail/u/0/#inbox/<id>`.
- Sent 2026-08-06 from account `nana.tutu.paa.kwesi26@gmail.com` (connection `gmail_jadish-naos`) to `bohene8@gmail.com` and `johnawotwi@gmail.com` — both `success_count:1, error_count:0`.

## Execution-mode caveats
- Interactive `hermes mcp add` password prompt is unreliable over non-TTY automation; pre-set env var and rerun.
- After wiring, must `hermes gateway restart` (see SKILL.md detached-watcher pattern) + start a new session before `mcp_composio_*` tools appear.