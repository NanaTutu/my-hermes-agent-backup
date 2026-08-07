---
name: kanban-board
description: Use when Tutu mentions the kanban or asks to work a task.
---

# Kanban board (Tutu + Hermes shared workbench)

Local-first board where Tutu writes tasks and tags them `@hermes` to open them
for Hermes to claim, work, and close.

## Location
- CLI: `python "C:\Users\bohen\kanban\kb.py"` (shell alias `kb`)
- Data: `C:\Users\bohen\kanban\tasks.json` (JSON, git-able, single-writer)
- Docs: `C:\Users\bohen\kanban\README.md`

## Command
## Command
```
kb add                                                            # INTERACTIVE prompt (title, desc, assignee, priority, tags)
kb add <title> [--desc ".."] [--priority p0..p3] [--assignee tutu|hermes] [--tags '["hermes"]'] [--status <s>]
kb list [--status backlog|todo|in_progress|blocked|done]
kb board
kb next                                  # top claimable @hermes task (backlog/todo only)
kb claim <id>                            # set in_progress, assignee hermes
kb move <id> <status> [--note ".."]     # statuses: backlog todo in_progress blocked done
kb show <id>
```
Priority p0 (urgent) .. p3 (someday). `next` sorts by priority then oldest created.
Bare `kb add` (no title) collects the fields from the user interactively. Non-
interactive flag form still works for script/cron use. Both support `--assignee`.

## Hand-off protocol (how Hermes works the board)
1. On demand: Tutu says "work task <id>" -> `kb claim <id>`, execute REAL work, then `kb move <id> done --note "..."`.
2. Autonomous self-pull (cron job "kanban self-pull", id 84c08fe54e8d, daily 09:00 UTC, delivers to Telegram DM):
   `kb next` -> if nothing, report clean and stop. Else `kb claim <id>`, `kb show <id>`, run real commands/read files
   and verify output (never fabricate), then `kb move <id> done --note`. Report evidence. Job is paused by default;
   resume only when Tutu asks, confirming cadence/scope first.

## Guardrails (non-negotiable)
- `kb next` / `kb claim` only touch tasks (a) in backlog/todo AND (b) tagged `@hermes` or assigned to hermes.
  Tasks tagged `@tutu` are NEVER claimable. Plain `kb list` / reading is always fine.
- Never claim, block, or guess on an ambiguous task: leave it and report what is missing.
- tasks.json is single-writer; kb.py write-then-renames atomically. Never hand-edit tasks.json while Hermes also
  writes it (concurrent writes lose updates).

## Pitfalls
- Windows `C:\...` paths work in git-bash; the `kb` alias only exists in the interactive shell, not raw `python`
  calls - always run `python "C:\Users\bohen\kanban\kb.py"` explicitly.
- `--tags` is a JSON array string; quote it.
- The cron self-pull runs in a fresh session with no chat memory: its prompt must be self-contained.