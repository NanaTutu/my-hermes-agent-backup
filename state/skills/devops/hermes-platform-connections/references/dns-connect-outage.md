# DNS / connect outage series — Aug 2026 (api.telegram.org unreachable)

Observed on Tutu's Windows box. Logs: `$HERMES_HOME/logs/gateway.log`; state:
`$HERMES_HOME/gateway_state.json`.

## Timeline
- 2026-08-07 ~22:44 UTC — `getaddrinfo failed` on api.telegram.org plus both
  fallback IPs; 8/8 connect attempts failed; watcher scheduled a 300s retry;
  reconnected 22:50:51 (attempt 1/8, after DoH fallback discovery). Down ~5 min.
- 2026-08-08 ~15:01 UTC — same signature; reconnected 15:06:44. Down ~5 min.
  Live probes minutes later: nslookup resolved, HTTPS 302 in 0.5s — network was
  fine post-recovery, i.e. the failure was transient at failure time.
- 2026-08-09 04:51 → 22:34 UTC — same signature but persistent. 06:19: poller
  escalated after 10 network-error retries ("Telegram polling could not reconnect
  after 10 network error retries. Escalating to gateway recovery." →
  "telegram queued for background reconnection" → "gateway staying alive,
  watcher will retry in background"). Watcher retried every ~5 min all day
  (attempt counter reached 86+); reconnected 22:34:27. Down ~17.5h. Recovery
  happened only when the box's network came back. Cron deliveries in the window
  (e.g. FX briefing 07:00 UTC) failed on `getaddrinfo failed`.

## Signature (identical all three days)
```
Primary api.telegram.org connection failed ([Errno 11001] getaddrinfo failed); trying fallback IPs 149.154.166.110, 149.154.167.220
Fallback IP 149.154.166.110 failed: All connection attempts failed
Fallback IP 149.154.167.220 failed: All connection attempts failed
Connect attempt N/8 failed: httpx.ConnectError: All connection attempts failed
Failed to connect to Telegram: httpx.ConnectError: All connection attempts failed
Reconnect telegram failed, next retry in 300s
```

## Adapter behaviors observed (useful, from log messages)
- Between retries the adapter tries DNS-over-HTTPS fallback discovery:
  "Discovering Telegram API fallback IPs via DNS-over-HTTPS…" /
  "DoH discovery yielded no usable IPs (system DNS: unknown); using seed fallback
  IPs …". A successful reconnect after an outage usually logs DoH discovery first.
- The 300s watcher keeps the gateway alive even with zero platforms connected:
  "No connected messaging platforms remain, but N platform(s) queued for
  reconnection — gateway staying alive, watcher will retry in background."
  Do NOT `hermes gateway restart` during a DNS outage expecting a fix — it hits
  the same wall; the outage is environmental, not a gateway fault.

## Diagnosis steps that worked
1. `hermes gateway status` — process alive ≠ platform connected.
2. `gateway_state.json` → `platforms.telegram.state` / `error_code` / `updated_at`.
3. Datestamp the outage window from the log:
   `grep -E "Reconnect telegram failed|All connection attempts failed"` +
   `grep "reconnected successfully"`.
4. Live network probe at check time: `nslookup api.telegram.org` and
   `curl -sS -o /dev/null -w "%{http_code}" https://api.telegram.org`
   (302 from a bare GET = reachable). Distinguishes "still down" from
   "already recovered".
5. Freshness check: `gateway_state.json` can lag the log by minutes — it can read
   `retrying` after a reconnect already landed. Trust the log line
   "✓ telegram reconnected successfully" + `updated_at` timestamp.

## Actionable takeaway
Recurring isolated DNS failures on the box (3 of 3 days, escalating duration)
→ check Windows DNS config / VPN / proxy; recommend static 8.8.8.8 or 1.1.1.1.
Outage windows also break cron deliveries — check `cronjob list` →
`last_delivery_error` for jobs that should have fired in the window.