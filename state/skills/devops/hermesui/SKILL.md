---
name: hermesui
description: "Use when troubleshooting Tutu's hermesUI web frontend."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [hermesui, hermes, web-ui, localhost, troubleshooting, gateway]
---

# hermesUI

Tutu's local ChatGPT-style web frontend for Hermes, at `C:\Users\bohen\hermesUI`.

## Architecture

- `server.py` — stdlib-only (`BaseHTTPRequestHandler` + `ThreadingHTTPServer`).
  Serves `static/` on `127.0.0.1:8080` and injects the backend session token +
  port into `index.html`. Binds **127.0.0.1 only** (IPv4, no `0.0.0.0`).
- `static/app.js` — vanilla JS, zero build step. Speaks the `tui_gateway`
  JSON-RPC dialect over WebSocket to the Hermes backend at
  `ws://127.0.0.1:9119/api/ws?token=...` (methods: `session.create/list/resume`,
  `prompt.submit`, `session.interrupt`, `model.options`, `image.attach_bytes`,
  `file.attach`, ...).
- Backend = `hermes serve --port 9119 --skip-build`, launched and
  health-checked by `server.py`, kept alive by a 30s watchdog thread that
  restarts it on death or token drift.
- `start.bat` / `stop.bat`; `hermesui.state.json` holds token + ports;
  `hermesui.log` is shared by BOTH the static server and the backend (backend
  stdout is redirected there); `hermesui.pid`.

## Quick health checks

```bash
netstat -ano | grep -E ':(8080|9119)'          # both should be LISTENING
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8080/   # 200 = page serves
curl -s -H "X-Hermes-Session-Token: <token>" http://127.0.0.1:9119/api/config  # live config
```

- `localhost:8080` works but is ~200ms slower than `127.0.0.1` (IPv6 `::1`
  fails first, then IPv4 fallback) — expected, not a fault.
- The backend's `/` and `/health` return 404 "Headless backend (hermes serve):
  web UI disabled" — that is EXPECTED. The real API lives under `/api/*`
  (e.g. `/api/config`, `/api/ws`).

## "Can't access you on localhost:8080" — the #1 cause

Symptom: the page loads (HTTP 200) but every chat message fails. The backend
is usually FINE — the problem is the *resumed session's pinned model*, not the
process. Sequence:

1. `tail -40 hermesui.log` and look for `HTTP 400 ... "Model is unavailable"`.
   The line names the dead model (e.g. `Provider: opencode-zen  Model:
   deepseek-v4-flash-free`).
2. Confirm it is persisted, not a fluke: the newest `request_dump_*.json` in
   `~/AppData/Local/hermes/sessions/` carries a `"model"` field and a
   `"reason": "non_retryable_client_error"`; `grep -c <model> state.db` shows
   the string baked into the session store (1,000+ hits = long-running pinned
   session).
3. **A restart does NOT fix this** — the session's model lives in `state.db`,
   so the watchdog/backend re-resumes the same dead model on every boot.
4. Fix (either):
   - In the web UI composer, send `/model deepseek-v4-pro` — switches the
     CURRENT session's model (session-scoped by default). Or `/model chatgpt`.
   - Reload the page — boot calls `session.create` with no model override, so
     the fresh session uses the configured default.

## Pitfalls

- **The model dropdown (`#model-select`) only affects NEW chats.** The frontend
  passes `S.selectedModel` to `session.create`, never to `prompt.submit`. To
  change the CURRENT session's model you MUST use the `/model` slash command,
  not the dropdown.
- **Free opencode-zen models get churned without notice.** `deepseek-v4-flash-free`
  was removed (HTTP 400). Keep the UI on the default `deepseek-v4-pro`
  (opencode-go) or a paid model; any session pinned to a free model will break
  this exact way again.
- The configured default: `model.default deepseek-v4-pro`, `provider opencode-go`,
  `base_url https://opencode.ai/zen/go/v1`; alias `chatgpt` → `openai-codex/gpt-5.5`.
