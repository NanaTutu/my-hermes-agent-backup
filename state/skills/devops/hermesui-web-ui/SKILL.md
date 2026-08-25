---
name: hermesui-web-ui
description: Operate and troubleshoot hermesUI, Hermes' local web UI.
---

# hermesUI — Local Web UI for Hermes

Tutu's local ChatGPT-style web client for Hermes at `C:\Users\bohen\hermesUI`. A stdlib-only `server.py` that (1) serves a vanilla-JS frontend on :8080, (2) ensures the Hermes backend (`hermes serve`) runs on :9119, and (3) injects a session token into `index.html` so the browser can authenticate its WebSocket upgrade.

## Architecture

- `server.py` (stdlib, no deps) — static server on 127.0.0.1:8080 + backend lifecycle manager + watchdog thread.
- `static/app.js` — vanilla JS, speaks the tui_gateway JSON-RPC dialect over `ws://127.0.0.1:9119/api/ws?token=...` (methods: `session.create/list/resume`, `prompt.submit`, `model.options`, …).
- Backend `hermes serve --port 9119 --skip-build` — headless gateway; only `/api/*` endpoints exist (no web UI — that's hermesUI's whole point).
- State files: `hermesui.state.json` (token + ports), `hermesui.pid`, `hermesui.log` (backend stdout/stderr is redirected here too).

## Start / stop

- Start: `start.bat` (auto-locates python, launches `pythonw server.py`). Logs `hermesUI ready → http://127.0.0.1:8080/`.
- Stop: `stop.bat` (kills pid + `hermes serve --stop`).
- A watchdog thread in `server.py` restarts the backend if it dies or its token drifts (every 30s).

## Troubleshooting "I can't access it on localhost:8080"

Run in order:

1. Confirm listeners: `netstat -ano | grep -E ':(8080|9119)'` — both LISTENING = servers up.
2. Test the page: `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/` — HTTP 200 means the static UI serves fine and the problem is downstream (backend/model), NOT the page.
3. Backend health: `curl -s -H "X-Hermes-Session-Token: <token>" http://127.0.0.1:9119/api/config` — returns the default model. Token lives in `hermesui.state.json`.
4. Read `tail hermesui.log` for the actual error.

### Most common root cause: session pinned to a dead model

Symptom: page loads (200), but every message returns HTTP 400 "Model is unavailable" in `hermesui.log`.

Why: a long-running session's model override is persisted in `~/.hermes/state.db`. If that model was removed by the provider (free-tier models churn without notice), every continuation of that session fails. **Restarting the backend does NOT fix it** — the model is stored in the session, not the process.

Verify:
- `hermes sessions list` to see active sessions.
- Grep the dead model string in `state.db` (binary grep works): `grep -c "model-name" state.db`.
- Request dumps `~/.hermes/sessions/request_dump_*.json` show the exact model + endpoint + HTTP 400 body.

Fix (either):
- In the web-UI chat box, send `/model <working-model>` (e.g. `/model deepseek-v4-pro`) — switches the CURRENT session's model (session-scoped by default).
- Or reload the page — on boot the frontend calls `session.create` with the default model, starting fresh.

Pitfall: the web UI's model dropdown only affects NEW chats. `S.selectedModel` is wired into `session.create`, not `prompt.submit`, so changing the dropdown does NOT switch the current session — only `/model` does.

## Prevention

- Don't leave the web UI pinned to free-tier models; they get removed without notice. Keep it on the configured default (`config.yaml` → `model.default`).
- `/model chatgpt` switches to the `openai-codex/gpt-5.5` alias.
