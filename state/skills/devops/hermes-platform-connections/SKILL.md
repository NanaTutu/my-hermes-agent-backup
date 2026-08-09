---
name: hermes-platform-connections
description: Diagnose and rebuild Hermes messaging platform connections.
---

# Hermes Messaging Platform Connections

Class of task: connecting, diagnosing, scrapping, and rebuilding Hermes gateway
messaging platforms (Telegram today; WhatsApp/Slack/Discord follow the same
pattern). Companion to `hermes-state-backup` — backup protects config state,
this governs platform connectivity.

## How Hermes platforms are wired (mental model)

- Each platform is a **bundled plugin** at
  `$HERMES_HOME/hermes-agent/plugins/platforms/<name>/` (e.g. `telegram/`).
  Nothing to install; never uninstall. `hermes plugins list --plain | grep <name>`
  shows `bundled` (not `enabled`) — that is normal; bundled platform plugins
  activate when credentials exist.
- `plugin.yaml` in the platform dir declares `requires_env` (mandatory secrets)
  and `optional_env`. **These env vars are the ONLY configuration knobs.**
  Platform config is env-var driven via `.env`, NOT config.yaml.
- `hermes secrets` CLI is ONLY for external secret managers (Bitwarden,
  1Password). It does NOT edit `.env`. Set platform credentials by editing
  `.env` directly (or via the setup wizard).
- `<platform>:` blocks inside config.yaml are per-platform **toolset
  allowlists** (which tools a platform session may use) — NOT credentials.
  Do not delete them when scrapping a connection.
- `hermes config unset KEY` removes config values.
- There is NO `hermes telegram` / `hermes whatsapp` CLI command —
  `hermes telegram --help` fails with "invalid choice". Setup is .env-driven.

## Diagnose connection state

1. `hermes gateway status` — shows the scheduled task + whether a gateway
   process is alive ("No gateway process detected" = down).
2. Read `$HERMES_HOME/gateway_state.json` — authoritative last-exit record:
   `gateway_state` (running/stopped), `exit_reason`, and
   `platforms.<name>.state` / `error_code` / `error_message`.
3. `tail logs/gateway.log` for the retry/conflict transcript.

## Common failure: telegram_polling_conflict

- Signature: `Conflict: terminated by other getUpdates request; make sure that
  only one bot instance is running` after 5 retries (~200s), then
  "No connected messaging platforms remain. Shutting down gateway cleanly."
- Meaning: another process (second Hermes/OpenClaw instance, or a session
  Telegram has not yet released) holds the SAME bot token.
- Fix: ensure no other process uses the token → `hermes gateway restart`.
  If it recurs, the token is genuinely held elsewhere — scrap and rebuild
  with a fresh bot token (see below).
- Restart expectation (observed 2026-08-06): with the SAME token, the
  reconnection watcher can briefly log "Connected to Telegram (polling mode)"
  and gateway_state.json flips to `connected` while the conflict ladder
  escalates 1/5 → 5/5 (~20s/30s/40s waits, 200s total) and the gateway then
  shuts down cleanly on its own ("Shutdown phase: all adapters disconnected").
  A mid-retry `connected` is NOT proof of health. Verification = gateway.log
  shows a stable polling loop with ZERO `conflict (N/5)` lines after the
  retry window; any `conflict` line means the restart failed and only a
  fresh bot token fixes it.

## Common failure: transient DNS / connect errors (getaddrinfo / All connection attempts failed)

- Signature: `[Errno 11001] getaddrinfo failed` on api.telegram.org, then
  fallback IPs 149.154.166.110 / 149.154.167.220 also fail with
  `All connection attempts failed`; `Reconnect telegram failed, next retry in
  300s`; after ~10 network-error retries:
  `Telegram polling could not reconnect after 10 network error retries.
  Escalating to gateway recovery.` then `No connected messaging platforms
  remain, but 1 platform(s) queued for reconnection — gateway staying alive,
  watcher will retry in background.`
- Meaning: the BOX lost DNS/route to Telegram — NOT a token conflict (see
  polling_conflict above) and not Telegram-side. Common on Windows with
  ISP/VPN resolvers that drop lookups intermittently.
- Diagnosis: 1) `gateway_state.json` → `state: retrying`,
  `error_code: telegram_connect_error`; 2) live-probe the network at check time
  (`nslookup api.telegram.org`; `curl -o /dev/null -w "%{http_code}"
  https://api.telegram.org` — HTTP 302 on a bare GET = reachable).
  Healthy at check time ≠ healthy at failure time; datestamp the outage window
  from the log, don't assume from the present.
- Escalation ladder: short blips (minutes) self-heal via the 300s watcher;
  long outages only recover when the network returns — the gateway will NOT
  self-restart into a working state mid-DNS-outage, and neither will a manual
  `hermes gateway restart` (environmental fault, not gateway fault).
  Fix the resolver (static 8.8.8.8/1.1.1.1) or the VPN/proxy.
- Stale-state pitfall: `gateway_state.json` lags the log — it can read
  `retrying` minutes after a successful reconnect. Confirm with the log line
  `✓ telegram reconnected successfully` and `updated_at`; re-read the file.
- Recurrence signal: the SAME DNS signature N days in a row, escalating in
  duration, means an environment problem to fix, not a gateway problem.
  Full timeline, transcript markers, and verification steps: see
  `references/dns-connect-outage.md` (2026-08 series, incl. the ~17.5h case).
- Side effect to check: any cron job with `deliver` to Telegram that fired
  during the outage window will show `last_delivery_error` (getaddrinfo
  failed) in `cronjob list` — reschedule/rerun it after recovery if needed.

## Scrap & rebuild from scratch (workflow)

1. Back up `.env`: `cp .env .env.bak.$(date +%Y%m%d_%H%M%S)`.
   Windows/bash caveat (observed 2026-08-06): the `$(date ...)` substitution
   chained with cp can trip the terminal hardline command parser and be
   unconditionally BLOCKED. Fall back to a static name:
   `cp .env .env.bak.pre-swap` (or split into separate minimal commands).
2. Strip the platform's vars:
   `grep -vE '^TELEGRAM_[A-Z0-9_]+=' .env > .env.tmp && mv .env.tmp .env`.
   Verify: `grep -cE '^TELEGRAM_' .env` → 0, and unrelated keys intact.
3. Confirm the plugin is still bundled (step in "How platforms are wired").
4. User obtains a FRESH token from the platform side (Telegram: @BotFather
   /newbot). A fresh bot sidesteps any stale-session conflict entirely.
5. Write the new vars into `.env` (`TELEGRAM_BOT_TOKEN` required;
   `TELEGRAM_ALLOWED_USERS` = user ID from @userinfobot;
   `TELEGRAM_HOME_CHANNEL` optional for cron/notification delivery).
6. Start the gateway and verify via `hermes gateway status` +
   `gateway_state.json` (`platforms.telegram.state` should be connected).

## Pitfalls

- Never print token values; redact any command output that could echo them.
- `logs/gateway.log` is append-only across gateway runs. After a rebuild, a
  naive `grep -c "polling conflict"` matches STALE lines from the old run and
  produces false positives (observed: 17 matches, 0 real). Verify with
  timestamp-filtered greps (`grep -E "^YYYY-MM-DD HH:1[4-9]"`) and trust
  `gateway_state.json` (`platforms.telegram.state: connected`) plus the log
  line `[Telegram] Connected to Telegram (polling mode)` as the authoritative
  success signals.
- Set `TELEGRAM_ALLOWED_USERS` in the same .env edit as the token, BEFORE
  restarting the gateway, or the owner's own messages are denied by the
  default deny-unknown-senders policy.
- The allowlist is a hard gate: unknown senders are ignored, and without it
  even the bot owner cannot message the bot.
- Verify a user-pasted token equals the stored one WITHOUT leaking it: compare
  sha256 prefixes (`sha256sum | cut -c1-12`) of both; "DIFFERENT: False" means
  it's the same dead token — don't waste a restart. Gotcha: passing the value
  as shell `$1` into a `python - <<'PY'` heredoc yields an EMPTY argv (no arg
  was set), and sha256("") = e3b0c44298fc is the tell. Pass secrets via an env
  var instead: `NEW="<token>" python - <<'PY'`.
- A polling conflict can be Telegram-side (stale held session) — a brand-new
  bot token eliminates the entire class of problem.
- Scrapping a connection = removing `.env` vars + optionally `config unset`
  config keys. It does NOT involve touching the platform plugin.

## References

- `references/telegram.md` — Telegram-specific env vars, adapter behavior,
  and the exact diagnosis transcript from the 2026-08 case.
- `references/dns-connect-outage.md` — 2026-08 DNS/connect outage series on
  Tutu's box (3 events, ~17.5h worst case): timestamps, log signature,
  adapter behaviors (DoH fallback discovery, 300s watcher), verified
  diagnosis steps, and the static-DNS recommendation.
