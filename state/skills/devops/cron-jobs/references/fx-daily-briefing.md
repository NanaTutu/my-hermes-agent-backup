# FX Daily Briefing & Review — live cron instance (created 2026-08-06)

Tutu's daily FX news + directional bias system. Ghana = UTC (no DST), so cron times ARE local times. Delivered to his Telegram DM.

## Job 1 — FX Morning Briefing
- **id:** `b5d6a9874a5d` · **schedule:** `0 7 * * *` (07:00 UTC, ~15 min before London open — the day's biggest volatility window)
- **skills:** `fx-trading` · **toolsets:** `web, terminal` · **deliver:** origin
- **Job contract:** scan overnight Asia moves, central-bank/rate-expectation news, commodities, risk sentiment; today's high-impact calendar (CPI, NFP, rate decisions, PMI) with UTC times; then BULLISH/BEARISH/NEUTRAL bias + one-line rationale + key level for the 7 majors (EUR/USD, GBP/USD, USD/JPY, USD/CHF, USD/CAD, AUD/USD, NZD/USD); top 2-3 invalidation events; risk-management reminder.
- **Framing rules baked in:** bias = probability ("evidence suggests"), never "will go"; never invent prices/consensus — report only what sources say; compact Telegram formatting; ends with the single clearest news-driven bias.

## Job 2 — FX Evening Review
- **id:** `5a6c746a1662` · **schedule:** `0 21 * * *` (21:00 UTC, after NY close)
- **skills:** `fx-trading` · **toolsets:** `web, terminal` · **deliver:** origin
- **Chained:** `context_from: ["b5d6a9874a5d"]` — injects the morning briefing's output so the review scores each pair's morning bias as matched / not matched / unclear (process review, not trader grading).
- **Job contract:** day recap (headlines, releases vs consensus, how majors closed per sources); score morning bias per pair; tomorrow's high-impact calendar; one process takeaway.

## Why this design
- Chaining turns the pair into a feedback loop: bias → outcome → lesson, which is the process-over-outcome discipline from `fx-trading`.
- Both jobs load `fx-trading` so every report follows Trading Mode (probabilistic, risk-first, honest about base rates).
- Honest limitation: news-driven bias, NOT a live quote feed — jobs state unverifiable prices as such. If Tutu wants live prices, wire a market-data API into the jobs.

## Adjustment recipe
- `cronjob list` → confirm `next_run_at` + `state: scheduled` before claiming the system is live.
- Edit: `cronjob update <id>` (schedule/prompt/skills); pause/resume/remove as needed. Never guess job IDs — list first.
- If the FX skill is renamed, update both jobs' `skills` arrays.
