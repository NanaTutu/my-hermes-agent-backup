---
name: kanban
description: Use when working tasks from the shared kanban board.
---

# Shared Kanban Board (Tutu + Hermes)

## What it is
A local-first kanban at `C:\Users\bohen\kanban` — Tutu's task queue that Hermes
can claim and execute. Tutu adds tasks, tags them `@hermes` when they are open
for pickup; Hermes claims the top task, works it, and marks it done. Built with
a stdlib-only Python CLI and a single human-readable JSON store (git-able, no
dependencies).

## Files
- `kb.py` — the CLI (plain Python 3, no external deps)
- `tasks.json` — the board data (source of truth)
- `README.md` — full docs and guardrail rules (authoritative; keep in sync)

## Commands (alias `kb` already in Tutu's .bashrc)
```
kb add "Title" --desc "..." --priority p0..p3 --tags '["hermes","research"]' [--status]
kb board                          # all columns at once
kb list [--status backlog|todo|in_progress|blocked|done]
kb show <id>                      # full detail incl. notes log
kb next                           # top unclaimed @hermes task (backlog/todo only)
kb claim <id>                     # assign to hermes + set in_progress
kb move <id> <status> [--assignee tutu|hermes] [--note "..."]
kb move <id> done --note "what was done"   # complete with a summary
kb --file <path> ...            # point at a different store
```
Priorities: p0 (urgent) .. p3 (someday). `next` sorts by priority then oldest
first. Tags are lowercase keywords; the tag `hermes` opens a task for pickup.

## Guardrails (non-negotiable)
- **Only tasks tagged `@hermes` or assigned to hermes are claimable.** A
  `@tutu` task in backlog is refused by `kb claim` with exit 1 — Tutu's work
  stays his. If you edit `kb.py`, re-test this refusal.
- `next` never returns tasks already `in_progress` / `done` / `blocked`.
- Single-writer store: Tutu and Hermes take turns; never run two concurrent
  writes (updates can be lost). Saves are atomic (tmp file + os.replace).

## Hand-off protocol
1. On demand: Tutu says "work task N" -> `kb claim N` -> execute with real
   tools (terminal/file/web) -> `kb move N done --note "..."` -> report evidence.
2. Scheduled self-pull: cron job `kanban self-pull` (job id `84c08fe54e8d`,
   daily 09:00 UTC, deliver `telegram:806045604`) — PAUSED by default. Resume
   with `cronjob action=resume` only after Tutu opts in. Its prompt encodes the
   full loop: next -> claim -> show -> execute -> move done -> report, with
   explicit honesty rules and claim guardrails.

## Editing kb.py — pitfalls
- Keep command signatures uniform — `cmd_*(board, args)` — because `main()`
  calls `args.func(board, args)`. A mixed `(args, board)` signature fails with
  `AttributeError: 'dict' object has no attribute 'tags'`.
- Config knobs live at the top of the file: `STATUSES`, `PRIORITIES`,
  `HERMES_TAG`, `DEFAULT_DATA_FILE`. Map any column/rename changes there.
- Test after edits: add -> next -> claim -> move done, plus the @tutu refusal
  (expect exit 1) and that `next` skips already-claimed tasks.