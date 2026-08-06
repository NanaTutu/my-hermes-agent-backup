# Telegram platform specifics

Session-specific detail and durable Telegram knowledge from the 2026-08
Tutu-Hermes rebuild. Environment: Windows, `$HERMES_HOME =
C:\Users\bohen\AppData\Local\hermes`.

## Plugin location

`$HERMES_HOME/hermes-agent/plugins/platforms/telegram/`
- `plugin.yaml` (manifest) — name `telegram-platform`, kind `platform`, v1.0.0.
- `adapter.py` — reads ALL settings via `os.getenv(...)`; no config.yaml keys.
- `telegram_network.py` — fallback direct-IP transport.

`hermes plugins list --plain | grep -i telegram` → `not enabled  bundled 1.0.0
telegram-platform`. Bundled + not enabled is NORMAL — it activates when
`TELEGRAM_BOT_TOKEN` exists.

## Environment variables (from plugin.yaml + adapter)

Required (`requires_env`):
- `TELEGRAM_BOT_TOKEN` — bot token from @BotFather (password:true).

Optional (`optional_env`):
- `TELEGRAM_ALLOWED_USERS` — comma-separated Telegram user IDs allowed to talk
  to the bot.
- `TELEGRAM_ALLOW_ALL_USERS` — allow any user (dev only).
- `TELEGRAM_HOME_CHANNEL` — default chat ID for cron/notification delivery.
- `TELEGRAM_HOME_CHANNEL_NAME` — display name for the home channel.

Other adapter-read env (behavioral):
- `GATEWAY_ALLOW_ALL_USERS` (fallback allow-all gate)
- `TELEGRAM_REQUIRE_MENTION`, `TELEGRAM_EXCLUSIVE_BOT_MENTIONS`
- `TELEGRAM_OBSERVE_UNMENTIONED_GROUP_MESSAGES`
- `TELEGRAM_GUEST_MODE`
- `TELEGRAM_FREE_RESPONSE_CHATS`
- `TELEGRAM_WEBHOOK_URL`, `TELEGRAM_WEBHOOK_SECRET`
- `HERMES_TELEGRAM_DISABLE_FALLBACK_IPS`

## Case transcript: telegram_polling_conflict (2026-08-06)

`gateway_state.json` fields observed:
```
gateway_state: stopped
exit_reason: "Telegram polling could not recover after 5 retries (200s total
wait). The previous gateway session is still held open on Telegram's servers,
or another process is using the same bot token ..."
platforms.telegram: { state: "fatal",
  error_code: "telegram_polling_conflict",
  error_message: "...Conflict: terminated by other getUpdates request; make
  sure that only one bot instance is running..." }
```

`logs/gateway.log` sequence: primary api.telegram.org connection failed →
fallback IP 149.154.166.110 → "Telegram polling retry 4/5 failed: Timed out" →
"polling conflict (5/5)" → "could not recover after 5 retries" → "Disconnected
from Telegram" → "No connected messaging platforms remain. Shutting down
gateway cleanly."

Finding: `tasklist //FI "IMAGENAME eq python.exe"` showed NO running gateway
process — token was not held locally, pointing at a Telegram-side stale session
or an external instance. Rebuild with a fresh token is the safe path.

## The exact rebuild I ran

Backup + strip (kept GITHUB_TOKEN, OPENCODE_ZEN_API_KEY etc.):
```
cp .env .env.bak.$(date +%Y%m%d_%H%M%S)
grep -vE '^TELEGRAM_[A-Z0-9_]+=' .env > .env.tmp && mv .env.tmp .env
grep -cE '^TELEGRAM_' .env    # → 0
```
`.env.bak.*` holds the old token — delete after the new bot is confirmed working.

The `telegram:` blocks at config.yaml lines 170/213 were toolset allowlists
(list of tool names under `telegram:`) — left untouched; not credentials.

## Getting the fresh token

- @BotFather → /newbot → name + username → returns the token. User does this
  in Telegram; cannot be done from the agent/CLI side.
- @userinfobot → user's numeric ID for `TELEGRAM_ALLOWED_USERS`.

## Verification after rebuild

- `hermes gateway status` → "Gateway process detected" / scheduled task OK.
- `gateway_state.json` → `platforms.telegram.state` no longer "fatal".
- `logs/gateway.log` → no conflict lines; connects on first poll.

## Second encounter (2026-08-06, same day, same dead token)

Repeat symptom hours later; the user's "new" token was byte-identical to the
stored one (caught by sha256-prefix compare — never echo tokens). Recorded
sequence after `hermes gateway restart` with the SAME token:

- 04:05:33 first connect failed with the same conflict error; watcher queued
  retry (gateway stayed up for cron).
- 04:06:04 reconnection attempt 2 logged "Connected to Telegram (polling
  mode)" and gateway_state.json flipped to `connected` — transient.
- 04:06:09 conflict (1/5) wait 20s → 04:06:36 conflict (2/5) wait 30s →
  04:07:12 conflict (3/5) wait 40s → ... → 5/5 → clean self-shutdown at
  04:09:59 ("Shutdown phase: all adapters disconnected"); gateway_state.json
  back to stopped/fatal/telegram_polling_conflict.

Lesson: `connected` in gateway_state.json during the reconnection window is
NOT health. The definitive check is a stable polling loop in gateway.log with
no `conflict (N/5)` lines. Restart with the same token is only worth ONE try
as cheap evidence; the fix remains a fresh @BotFather token.

Terminal quirk on this host: `cp .env .env.bak.$(date +%Y%m%d_%H%M%S)` was
hardline-BLOCKED (command parser); static `cp .env .env.bak.pre-swap` worked.
Backup the .env BEFORE waiting for the user's fresh token so the old token is
preserved as a rollback point.