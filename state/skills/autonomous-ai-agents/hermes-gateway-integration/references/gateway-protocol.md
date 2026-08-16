# Hermes Gateway — Protocol Reference

Condensed field-level reference, reverse-engineered from
`hermes_cli/web_server.py`, `tui_gateway/server.py`, and
`apps/shared/src/*` (Hermes venv at `~/.hermes/hermes-agent/` on POSIX,
`%LOCALAPPDATA%/hermes/hermes-agent/` on Windows). Re-verify against those files
when anything looks stale — this is a snapshot, not the source of truth.

## Full RPC method registry

Enumerate live with: `grep -n '@method(' tui_gateway/server.py | sed ...`.

Core chat methods (verified working):
`session.create`, `session.list`, `session.most_recent`, `session.active_list`,
`session.activate`, `session.resume`, `session.history`, `session.delete`,
`session.title`, `session.undo`, `session.compress`, `session.interrupt`,
`session.status`, `session.save`, `session.usage`, `session.context_breakdown`,
`session.branch`, `session.steer`, `session.cwd.set`, `session.redirect`,
`prompt.submit`, `prompt.background`, `model.options`, `model.disconnect`,
`model.save_key`, `config.get`, `config.set`, `config.show`.

Interactive/approval replies: `clarify.respond`, `approval.respond`,
`sudo.respond`, `secret.respond`, `terminal.read.respond`.

Attachments: `file.attach`, `image.attach`, `image.attach_bytes`, `image.detach`,
`pdf.attach`, `input.detect_drop`.

Everything else (agents, billing, browser, cron, learning, pets, plugins,
projects, rollback, shell, skills, spawn_tree, tools, voice, …) — see the
registry; don't assume a method doesn't exist without grepping it.

## Method return shapes (observed)

`session.create` →
```json
{ "session_id": "<8-hex live sid>",
  "stored_session_id": "<YYYYMMDD_HHMMSS_xxxx durable>",
  "message_count": 0,
  "messages": [],
  "info": { "model": "deepseek-v4-pro", "provider": "...", "cwd": "...",
            "branch": null, "project": null, "tools": {}, "skills": {},
            "lazy": true, "desktop_contract": "...", "profile_name": "..." } }
```
Params honored: `model`, `provider`, `reasoning_effort`, `fast`, `messages`
(seed history as `[{role, content}]`), `title`, `parent_session_id`, `cwd`,
`profile`, `close_on_disconnect`, `cols`.

`session.list` → `{ "sessions": [ { "id": "<durable>", "title": "", "preview": "",
"started_at": 0, "message_count": 0, "source": "webui" } ] }`
(deny-list filters source `tool`; `limit` default 200, over-fetches 2x then trims.)

`session.resume` → `{ "session_id": "<new live sid>", "messages": [...], "info": {...} }`
(Accepts the durable id OR title; follows compression-continuation chains.)

`session.history` → `{ "count": N, "messages": [ {role, text, ...} ] }`
Message roles: `user`, `assistant`, `tool` (→ `{role:"tool", name, context}`),
`system`. Assistant messages carry reasoning under keys `reasoning`,
`reasoning_content`, `reasoning_details`, `codex_reasoning_items` (coerce to
text — the value may be a string, an array of blocks, or an object). User
messages may carry `display_kind:"skill_invocation"`.

`prompt.submit` → `{ "status": "streaming" }` (returns immediately; the deferred
agent build may still be in flight — the turn streams once ready).

`model.options` → `{ "providers": [ { "slug", "name", "models": ["<id>", ...], "total_models", ... } ], "model": "<current>", "provider": "<current>" }`
(`models` is a flat list of model-id strings.)

## Event payload details (verified live)

- `message.start` `{}` — emitted at turn start, before the first delta.
- `message.delta` `{"text": "<chunk>", "rendered?": "<ansi>"}` — `rendered` is
  ANSI-colored; ignore it for HTML rendering, render `text` yourself.
- `message.complete` `{"text": "<full>", "usage": {"model","input","output",
  "reasoning","prompt","completion","total","calls","context_used","context_max",
  ...}, "status": "complete"|"error"|"interrupted", "rendered?": ..., 
  "error?": ..., "reasoning?": ..., "warning?": ..., "billing?": ...}`.
  **`text` is the full final reply — authoritative.**
- `thinking.delta` `{"text"}` (model "musing" lines), `reasoning.delta`
  `{"text","verbose?"}`, `reasoning.available` `{"text"}`.
- `tool.start` `{"tool_id","name","context","args_text?"}` (args only when
  verbose), `tool.complete` `{"tool_id","name","args","duration_s?","result?",
  "summary?","result_text?","inline_diff?","todos?"}`, `tool.generating`
  `{"name"}`, `tool.output_risk` `{"name","risk","findings","redacted"}`.
- `status.update` `{"kind","text"}`.
- `session.info` `{"model","provider","cwd","branch","project",...}`.
- `clarify.request` / `approval.request` / `sudo.request` / `secret.request` —
  payloads carry `choices` and a prompt; reply via the matching `.respond` method.
- `error` `{"message?"}` — gateway-level error (not a provider error).

## Auth internals (for debugging)

- `_SESSION_TOKEN = os.environ.get("HERMES_DASHBOARD_SESSION_TOKEN") or secrets.token_urlsafe(32)`.
- `_SESSION_HEADER_NAME = "X-Hermes-Session-Token"` (also accepts `Bearer`).
- `_is_accepted_host(host, bound)` strips `:port` (IPv6 bracket-aware); loopback
  bind accepts `localhost`/`127.0.0.1`/`::1` regardless of port.
- `_ws_client_is_allowed`: loopback bind → peer IP must be loopback; explicit
  non-loopback bind → any peer (auth is the real gate).
- `_ws_auth_reason`: loopback → `?token=` constant-time; gated → `?ticket=`
  (single-use, 30s TTL) or `?internal=` (server-spawned children only);
  `?token=` is unconditionally rejected in gated mode.
- `should_require_auth(host)` → `host not in {localhost,127.0.0.1,::1}` (RFC1918
  is treated as PUBLIC — LAN exposure always gated).

## Attachment methods (field-level)

`image.attach_bytes {session_id, content_base64|data, filename?, ext?}` →
`{attached:true, path, count, remainder:"", text:"[User attached image: <name>]", bytes}`.
Decodes an optional `data:image/...;base64,` prefix; sniffs ext from filename then
magic bytes (PNG/JPEG/GIF/WebP/BMP; fallback `.png`); cap 25 MB (error 4018).

`file.attach {session_id, path?|data_url?, name?}` →
`{attached:true, name, path, ref_path, ref_text:"@file:<...>", uploaded}`.
`data_url` is `data:<mime>;base64,<b64>` (required when the client file isn't
visible to the gateway). `ref_path` is workspace-relative; append `ref_text` to
the prompt text so the agent reads the file.

`pdf.attach {session_id, path?|content_base64?, filename?, first_page?, last_page?}` →
`{attached, filename, pages_attached, pages:[{path,page,...}], count}`.
Requires `pdftoppm` (error 5028 if missing); renders 150-DPI PNGs; cap 50 MB / 25 pages.

`image.detach {session_id, path}` → `{detached, count}` — unqueue an image by the
path that `image.attach(_bytes)` returned.

## Reusable verification probe

`scripts/gateway_smoke_test.py <token>` — run with the Hermes venv python (has
aiohttp). It proves the exact endpoint/token/streaming your client relies on.
