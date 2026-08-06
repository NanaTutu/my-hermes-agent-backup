---
name: cron-jobs
description: Use when creating, chaining, or managing cron jobs.
---

# Hermes Scheduled Cron Jobs

## When to use
- User asks for anything "daily", "every N hours", or "at a specific time": news briefings, reviews, reminders, watchdogs, monitors.
- A task must outlive the current session and run unattended (a cron run is a fresh session with no chat context).
- A later job needs the output of an earlier job (chained review workflows).

## Core mechanics (cronjob tool)
- `create` requires `schedule` + `prompt`; optional: `name`, `skills` (loaded before the prompt runs), `enabled_toolsets`, `context_from`, `deliver`, `repeat`, `no_agent`+`script`.
- Schedule formats: `'30m'`, `'every 2h'`, cron `'0 7 * * *'`, ISO one-shot `'2026-08-07T09:00:00'`.
- `deliver`: omit → origin (current chat/topic — recommended); `'local'` = save only; `'all'` = every connected channel; explicit `platform:chat_id[:thread]` for elsewhere.
- `enabled_toolsets`: restrict to what the job needs (e.g. `["web","terminal"]`) to cut token overhead.
- `no_agent: true` + `script`: pure-script watchdog — empty stdout = silent (nothing sent), non-empty = delivered verbatim; non-zero exit/timeout sends an error alert.

## Chaining pattern (review workflows)
- `context_from: [jobId]` injects that job's MOST RECENT COMPLETED output into the new job's prompt.
- Classic use: morning briefing → evening review that scores the morning bias against what actually happened (process feedback loop).
- Caveat: it injects the most recent completed output; it does NOT wait for an upstream job running in the same tick.

## Rules & pitfalls
- Prompts MUST be self-contained: no chat memory in cron runs. Include the timezone anchor (e.g. "07:00 UTC = Ghana morning"), the full task, output format, and honesty rules.
- Jobs run with NO user present: no clarify tool, no questions — decide sensible defaults inside the prompt.
- Never schedule recursive cron jobs from inside a cron run.
- UTC is the scheduling reference; when the user's local time matters, state it in the prompt (Ghana = UTC, no DST).
- Include in autonomous research prompts: "do not invent data — report only what sources say; flag unverifiable figures" (prevents fabricated news/prices).
- Verify a job is live before claiming it: `cronjob list` → check `next_run_at` and `state: scheduled`.

## References
- `references/fx-daily-briefing.md` — live instance: the daily FX briefing/review pair (job IDs, chaining, UTC anchors, output contract).
