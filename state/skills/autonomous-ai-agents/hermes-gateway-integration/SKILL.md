---
name: hermes-gateway-integration
description: Use when building a client on the Hermes serve gateway.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, gateway, json-rpc, websocket, web-ui, integration, protocol]
    related_skills: [hermes-agent]
---

# Hermes Gateway Integration

How to drive Hermes Agent's backend gateway programmatically and build custom
surfaces (web UIs, scripts, IDE/mobile clients) on top of it — WITHOUT
reimplementing the agent core.

## Mental model

Hermes ships one canonical backend server: **`hermes serve`** (default
`127.0.0.1:9119`). The official desktop app, the web dashboard's embedded chat,
and the Ink TUI all speak the *same* newline-delimited JSON-RPC dialect to it.
You can write your own client against that same dialect — same agent, same
tools, same memory and skills, just your own surface.

Two things shape every design decision:
- **The gateway is the waist.** Don't reimplement agent orchestration — call
  `session.create` / `prompt.submit` and render the event stream.
- **The desktop/dashboard already exist** (`hermes desktop`, `hermes
  dashboard`). Build a custom client only when the user wants a *dedicated*
  surface (e.g. a lightweight chat-only UI) — and say so honestly.

## Endpoint + auth (the part everyone gets wrong first)

- WebSocket: `ws://127.0.0.1:9119/api/ws?token=<TOKEN>`
- REST (mostly optional — the chat flow is all WS): `/api/*` with header
  `X-Hermes-Session-Token: <TOKEN>` (or `Authorization: Bearer <TOKEN>`).
- **Token** (`_SESSION_TOKEN`): set by env var `HERMES_DASHBOARD_SESSION_TOKEN`
  when you launch `hermes serve`; otherwise random per boot. The official UI
  injects it into served HTML as `window.__HERMES_SESSION_TOKEN__`. **Control it
  yourself by setting the env var** so your client always knows the token.
- **Loopback mode** (bound to `127.0.0.1`): no auth gate; `?token=` on the WS
  upgrade is constant-time compared. Client peer IP must be loopback.
- **Gated mode** (non-loopback bind, e.g. `--host 0.0.0.0`): `?token=` is
  REJECTED; clients must fetch a single-use `?ticket=` from
  `POST /api/auth/ws-ticket` (cookie-auth) or present `?internal=` (server-spawned
  children only). `--insecure` is a NO-OP as of the June 2026 hardening.
- **Host/Origin guard strips ports** (`_is_accepted_host` in
  `hermes_cli/web_server.py`): a frontend served on ANY localhost port can WS-connect
  directly to `localhost:9119` — no CORS problem, no proxy needed. (Hostname must
  be a loopback name; port is ignored.)

Public (no-token) REST endpoints: `/api/health`, `/api/status`,
`/api/config/defaults`, `/api/config/schema`, `/api/model/info`.

## Protocol framing

- Request: `{"jsonrpc":"2.0","id":<int|str>,"method":"<name>","params":{...}}`
- Response: `{"jsonrpc":"2.0","id":<same>,"result":{...}}` or `{...,"error":{code,message}}`
- Events (unsolicited): `{"method":"event","params":{"type":"<event>","payload":{...},"session_id":"<live sid>"}}`
- Request → response correlates on `id`; events interleave freely. Filter events
  by `session_id` when multiple sessions are live.

## Core methods

| Method | Params | Returns |
|---|---|---|
| `session.create` | `{model?, provider?, messages?, title?}` | `{session_id (live), stored_session_id (durable), messages, info:{model, provider, cwd, ...}}` |
| `session.list` | `{limit?}` | `{sessions:[{id (durable), title, preview, started_at, message_count, source}]}` |
| `session.resume` | `{session_id (durable id)}` | `{session_id (new live sid), messages, info}` |
| `session.history` | `{session_id (live sid)}` | `{count, messages:[{role,text,reasoning?,display_kind?,...}]}` |
| `prompt.submit` | `{session_id (live), text}` | `{status:"streaming"}` then events |
| `session.interrupt` | `{session_id}` | stop the in-flight turn |
| `session.delete` / `session.title` | `{session_id, title?}` | delete / rename |
| `model.options` | `{include_unconfigured?, refresh?}` | `{providers:[{slug,name,models:[str]}], model, provider}` |

Key distinction: `session.create`/`session.resume` return a **live sid**; the
sidebar `session.list` and `session.resume`/`session.delete`/`session.title`
take the **durable stored id**. `prompt.submit`/`session.interrupt`/
`session.history` take the **live sid**.

## Event stream (payload shapes)

- `message.start` `{}` — turn started (create the assistant bubble here).
- `message.delta` `{text, rendered?}` — streamed tokens (live display only).
- `message.complete` `{text (authoritative full), usage, status:"complete"|"error"|"interrupted", rendered?, error?, reasoning?}` — turn ended.
- `thinking.delta` / `reasoning.delta` `{text, verbose?}` — reasoning stream.
- `tool.start` `{tool_id, name, context, args_text?}` → `tool.complete`
  `{tool_id, name, args, duration_s?, result?, summary?, result_text?, inline_diff?, todos?}`.
- `status.update` `{kind, text}` — transient progress line.
- `session.info` `{model, provider, cwd, branch, project, ...}` — model/cwd changes.
- `error` `{message?}`, `reaction` `{kind}`, `notification.show` `{text}`,
  `message.interim` `{text, already_streamed}` (commentary alongside tool calls).

## Attachments (files & images)

Stage attachments BEFORE `prompt.submit` — the next submit consumes them.

- **Images** → `image.attach_bytes {session_id, content_base64 (or data), filename?}`.
  Accepts a `data:image/...;base64,` prefix. Writes into the gateway's own
  `images/` dir and queues on the session; the next `prompt.submit` auto-includes
  them (native vision pipeline). Cap 25 MB. Returns `{attached, path, count,
  text, bytes}`. `image.attach` takes a host-local `path` instead (local mode
  only); `image.detach {session_id, path}` unqueues.
- **Files** → `file.attach {session_id, data_url (data:<mime>;base64,...), name?}`.
  Stages the file in the workspace and returns `{attached, name, path, ref_path,
  ref_text, uploaded}` where `ref_text` is `@file:<path>`. **You must append
  `ref_text` to the prompt text yourself** — the agent reads it via
  `agent.context_references` / its file tools. This is the no-dependency path for
  arbitrary files (PDFs, code, text) and works with ANY model.
- **PDF-as-vision** → `pdf.attach {session_id, content_base64, filename?}` renders
  pages to PNG via `pdftoppm` (poppler-utils, usually ABSENT on Windows) and
  queues the pages as images; cap 50 MB / 25 pages; returns 5028 if pdftoppm is
  missing. Prefer `file.attach` for PDFs when pdftoppm isn't installed.

Gotchas:
- **Images need a vision-capable model.** The default model may be text-only;
  `image.attach_bytes` still succeeds (the image is queued) but a text model
  won't "see" it. File attachments work with any model.
- The image queue is cleared on every `prompt.submit`, so attach immediately
  before the submit for that turn (don't attach speculatively early).
- Browser clients: read files with `FileReader.readAsDataURL` and pass the data
  URL straight through as `content_base64` / `data_url` (both accept the `data:`
  prefix). Stage client-side, then fire the attach RPCs right before submit.

## Critical gotchas

1. **`message.complete.text` is the authoritative full reply.** Deltas are for
   live rendering only. A single-chunk/non-streaming response (short answers,
   some providers) emits ZERO `message.delta` events and the whole text arrives
   only in `message.complete.text`. A robust renderer: append deltas live, then
   on `message.complete` REPLACE the accumulated text with `payload.text` when
   present. Using "only if empty" is wrong — it can drop a missing tail token.
2. `session.create` returns quickly; the expensive agent build is **deferred to
   the first `prompt.submit`** (cold boot can be 30–60s; the submit still
   returns `{status:"streaming"}` and streams when ready).
3. An empty new session has NO durable DB row until the first real turn — so it
   won't appear in `session.list`. That's fine (no orphan rows).
4. `message.complete` also carries `status:"interrupted"` after a stop; its
   `text` may be partial (good — render it) or `""` (keep the deltas).
5. First backend boot is slow (~40s cold, providers/skills/MCP); subsequent
   boots are ~5s (warm caches). Design launchers to REUSE a healthy backend
   (probe `/api/health` + a token-gated endpoint like `/api/config`).

## Troubleshooting "can't access / won't reply" (page loads, agent silent)

The #1 cause is NOT the servers being down — it's a **session pinned to a model
that is no longer available** (free-tier models get churned/removed upstream
without notice). Diagnose in this order:

1. `netstat -ano | grep -E ':(8080|9119)'` — both listeners present = servers up.
2. `curl http://127.0.0.1:8080/` → HTTP 200 = static UI fine.
3. `curl -H "X-Hermes-Session-Token: <token>" http://127.0.0.1:9119/api/config`
   → the `"model"` field. If it's healthy but the backend log shows a *different*
   model failing, the default is fine and a SESSION is pinned elsewhere.
4. Read the backend log — `"Model is unavailable"` / HTTP 400 with an explicit
   `Model:` + `Endpoint:` line is the signature.
5. `grep -c "<dead-model>" ~/AppData/Local/hermes/state.db` plus the newest
   `~/AppData/Local/hermes/sessions/request_dump_*.json` (filename embeds the
   stored session id; body carries `request.body.model` + `reason`).

**Fix (session-scoped):** send `/model <working-model>` (e.g. `/model
deepseek-v4-pro`) — `prompt.submit` forwards `/...` text to the slash-command
handler, which re-pins the current session. Or start a new chat / reload the
page to get a fresh session on the configured default.

**Restart does NOT help** — the session's model is persisted in state.db at
`session.create` time and re-resumed on boot.

**Pitfall:** a frontend model dropdown that only feeds `session.create` (not
`prompt.submit`) cannot switch a live session's model. Only `/model` re-pins a
live session — don't tell the user to use the dropdown to fix one.

Full command set + the 2026-08-25 case study: `references/troubleshooting-model-unavailable.md`.

## Building a client: the proven pattern (zero-dependency)

1. **Own the backend**: launcher generates a token, starts `hermes serve
   --port 9119 --skip-build` with `HERMES_DASHBOARD_SESSION_TOKEN=<token>`
   (detached), and polls `/api/health` until ready. `--skip-build` avoids the
   npm web-UI build — the gateway routes don't need it.
2. **Inject the token**: serve your `index.html` with a `__TOKEN__` placeholder
   substituted, so the browser never needs a token round-trip and no CORS/proxy
   layer is required (loopback host check strips ports).
3. **Frontend = vanilla JS** JSON-RPC client (connect → `session.create` →
   render events). No CDN, no build step → works offline.
4. **Launchers**: `start.bat`/`stop.bat` that resolve python (pythonw→python→py
   → absolute venv path) and idempotently reuse a running instance
   (EADDRINUSE → open browser to the existing URL instead of crashing).

## Running a client server on Windows (deployment gotchas)

These bit hard and are easy to re-hit; all verified against a real hermesUI build.

1. **`SO_REUSEADDR` silently lets a second process bind the same port.** Python's
   `ThreadingHTTPServer` defaults to `allow_reuse_address = True`; on Windows that
   lets a second instance bind the SAME port (port hijacking) instead of raising
   EADDRINUSE — so double-launch detection via `bind()` never fires and two
   processes "own" 8080. Fix: subclass and set `allow_reuse_address = False`, so a
   second launch fails cleanly and the launcher can point at the running instance.
2. **`pythonw.exe` has no stdout/stderr** (`sys.stdout is None`), so `print()` raises
   `AttributeError`. A windowless daemon MUST guard logging:
   `if sys.stdout is not None: print(...)` — and always also append to a log file.
3. **`schtasks /Create` is admin-denied in a non-elevated shell** ("Access is
   denied"), even for a per-user ONLOGON task. Use the **Startup folder** instead —
   no elevation needed. Create
   `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\<app>.lnk` via PowerShell
   COM: `$W=New-Object -ComObject WScript.Shell; $s=$W.CreateShortcut('<lnk>'); $s.TargetPath='<pythonw>'; $s.Arguments='<server.py> --no-open'; $s.WorkingDirectory='<dir>'; $s.WindowStyle=7; $s.Save()`.
   Single-quoted PS strings are literal, so paths with spaces are fine; run `server.py --no-open`
   so auto-start doesn't pop a browser at login.
4. **Self-healing = watchdog + detached backend.** Spawn `hermes serve` with
   `subprocess.Popen(..., creationflags=DETACHED_PROCESS|CREATE_NEW_PROCESS_GROUP)`
   (POSIX: `start_new_session=True`), then run a daemon thread that probes
   `/api/health` every ~30s and restarts the backend on `down`/`wrong_token`. A
   client-only health probe (`/api/health`, public) plus a token-gated probe
   (`/api/config`) distinguishes "backend down" from "wrong token".
5. **A backend spawned by an agent-terminal-launched script dies with it.** The
   Hermes `process.kill` is a TREE kill, so `hermes serve` launched from a
   `terminal(background=true)` script's `Popen` gets killed too, even with
   DETACHED_PROCESS. For a truly independent daemon, launch via
   `powershell Start-Process -WindowStyle Hidden` (or the Startup .lnk above),
   which creates a process outside the session tree.

## Verification (always do this — never claim a client works untested)

1. **Protocol probe** — `scripts/gateway_smoke_test.py <token>` (aiohttp,
   already in the Hermes venv) does `session.create` → `prompt.submit` →
   counts `message.delta` → `session.list` → `session.history`. Confirms the
   exact endpoint/token/streaming your client will hit.
2. **Render check** — headless Chrome against the served UI:
   `"<chrome>" --headless=new --screenshot="C:/abs/path.png" --virtual-time-budget=12000 --window-size=1280,800 http://127.0.0.1:8080/`
   then view the PNG. Note `--screenshot` needs a WINDOWS-style absolute path
   (`C:/...`, not `/c/...`). `--dump-dom` shows whether init JS ran (look for
   your connection-state text) but virtual time fast-forwards past real WS
   handshakes, so the "connected" model badge may lag — don't treat that as a bug.

## Source of truth (re-derive from here when stale)

- `hermes_cli/web_server.py` — routes, `_SESSION_TOKEN`, `_ws_auth_ok`,
  `_is_accepted_host`, `PUBLIC_API_PATHS` (`dashboard_auth/public_paths.py`).
- `tui_gateway/server.py` — the `@method(name)` registry, `dispatch()`, event emits.
- `apps/shared/src/json-rpc-gateway.ts` — client framing; `websocket-url.ts` — URL building.
- Enumerate all RPC methods: `grep -n '@method(' tui_gateway/server.py`.

Full method/event/field reference: `references/gateway-protocol.md`.
