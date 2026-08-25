# Troubleshooting "Model is unavailable" on a gateway client

Concrete case: 2026-08-25, hermesUI on Windows. User reported "can't access you
on localhost:8080". Page loaded; every reply died. Not a server-down problem.

## Diagnostic commands (in order)

1. Is anything listening?
   ```
   netstat -ano | grep -E ':(8080|9119)'
   ```
2. Does the static UI serve?
   ```
   curl -s -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:8080/
   ```
   Also test `localhost` vs `127.0.0.1`: the server binds `127.0.0.1` (IPv4)
   only, so `localhost` resolves `::1` first, fails, falls back to IPv4
   (~0.2 s slower). That latency is normal — not a bug.
3. What model does the backend currently resolve? (token lives in
   `hermesui.state.json` under `token`.)
   ```
   curl -H "X-Hermes-Session-Token: <token>" http://127.0.0.1:9119/api/config
   ```
   Case result: `"model":"deepseek-v4-pro"` — healthy — yet the log was failing
   on a DIFFERENT model. That mismatch is the tell: the DEFAULT is fine, a
   SESSION is pinned elsewhere.
4. Read the backend log (hermesUI redirects `hermes serve` stdout here):
   ```
   tail -40 C:/Users/bohen/hermesUI/hermesui.log
   ```
   Signature lines:
   ```
   ⚠️  API call failed ... BadRequestError [HTTP 400]
      Provider: opencode-zen  Model: deepseek-v4-flash-free
      Endpoint: https://opencode.ai/zen/v1
      Error: HTTP 400 ... Model is unavailable.
   ```
5. Confirm which session is pinned and how badly:
   ```
   grep -c "deepseek-v4-flash-free" ~/AppData/Local/hermes/state.db   # 1131 hits
   ls -t ~/AppData/Local/hermes/sessions/request_dump_*.json | head
   ```
   The `request_dump_<stored_session_id>_<timestamp>_<rand>.json` filename
   embeds the durable session id; the newest dump's `request.body.model` and
   top-level `reason` confirm the pinned dead model and why it failed.

## Root cause

The session was created when the default (or a picked) model was
`deepseek-v4-flash-free`. The model is persisted per-session in `state.db` and
re-applied on every continuation. The provider later removed the free model, so
every turn returns HTTP 400 "Model is unavailable". Restarting `hermes serve`
re-resumes the SAME session on the SAME dead model — no help.

## Fix

- Keep the current chat: send `/model deepseek-v4-pro` (session-scoped slash
  command; re-pins the live session).
- Or start a new chat / reload the page → fresh session on the configured
  default model.

## Why the hermesUI model dropdown did not help

`static/app.js` stores the dropdown in `S.selectedModel` and passes it only to
`session.create` (new chats). `prompt.submit` sends `{session_id, text}` with no
model, so a live session keeps its pinned model. Only the `/model` slash command
re-pins a live session.

## Prevention

Free-tier opencode-zen models get churned without notice. Don't pin long-lived
sessions to free models; keep them on the configured default (deepseek-v4-pro)
or a paid provider.
