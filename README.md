# Hermes State Backup

Portable, secrets-free mirror of **Tutu's Hermes Agent** configuration state,
synced to GitHub so the same persona, memory, skills, and cron jobs can be
recreated on any machine — by a human or by another agent.

**If you are an AI agent reading this:** you are looking at the durable
identity of one Hermes instance, *not* application source code. You will do one
of two things here:

1. **Consume** — restore this agent's state onto your own `$HERMES_HOME`.
2. **Update** — push new state back to this repo.

Read **Roles** first. Only one machine is allowed to push.

## Repo layout

| Path | What it is | Portable? |
|---|---|---|
| `state/SOUL.md` | Agent persona / system prompt | ✅ deployed to consumers |
| `state/memories/` | `MEMORY.md` + `USER.md` — durable memory + user profile | ✅ |
| `state/skills/` | Installed skills (grouped by category) | ✅ |
| `state/cron/jobs.json` | Scheduled job definitions | ✅ |
| `state/scripts/` | Portable helper scripts (routing, mixer/TV control) | ✅ |
| `state/config.yaml` | Settings (never credentials) | ❌ machine-local |
| `state/gateway_state.json`, `state/channel_directory.json` | Routing / channel state | ❌ machine-local |
| `state/context_length_cache.yaml`, `state/provider_models_cache.json` | Caches | ❌ machine-local |
| `hermes_backup.py` | AUTHOR-side: mirror → scan → commit → push | — |
| `hermes_sync.sh` | Role-aware entry point (author=push, consumer=pull+deploy) | — |

## Model routing (OpenCode Go)

This state ships an intent→model router for the `opencode-go` provider:

- **Aliases** — `state/config.yaml` under `model.aliases` defines one-word
  `/model` switches (`code`, `repo`, `vision`, `eye`, `write`, `long`, `fast`,
  `flash`, `cheap`, `reason`) mapped to the best OpenCode Go model per intent.
  Aliases live in `config.yaml`, which is author-side only and not deployed to
  consumers — re-apply on a fresh box.
- **Skill** — `state/skills/autonomous-ai-agents/model-router/` classifies a
  task's intent and recommends (or one-shot-executes) the best model.
- **Script** — `state/scripts/route_model.py` is a rule-based classifier:
  `python route_model.py "<prompt>"` prints the model + alias; `--list` shows
  the full table.

## Roles — single writer / many readers

This repo has exactly **one writer**.

- **AUTHOR** = the Windows box (`C:\Users\bohen`). It is the *only* machine
  that pushes. The `hermes-backup` plugin's `on_session_finalize` hook runs
  `hermes_backup.py` on every session exit.
- **CONSUMER** = any other box (Linux / macOS / BSD). It pulls
  fast-forward-only and deploys the portable subset. It **never** pushes.

`hermes_sync.sh` auto-detects the role from the OS (Windows → author, anything
else → consumer). Override with `HERMES_ROLE=author|consumer`.

## Consume — restore onto a new agent

```bash
git clone https://github.com/NanaTutu/my-hermes-agent-backup.git
cd my-hermes-agent-backup
./hermes_sync.sh                 # auto role, or: HERMES_ROLE=consumer ./hermes_sync.sh
```

The script pulls fast-forward-only, then copies **only the portable trees**
(`SOUL.md`, `skills/`, `memories/`, `cron/`, `scripts/`) into `$HERMES_HOME` (`~/.hermes`
on Unix, `%LOCALAPPDATA%\hermes` on Windows).

It deliberately does **not** touch machine-local files — `config.yaml`,
`gateway_state.json`, `channel_directory.json`, and the caches — because those
encode local paths, API identity, routing, and process state that legitimately
differ between boxes.

To restore by hand (no script), copy the portable trees into `$HERMES_HOME`
directly. Secrets (`auth.json`, `.env`) must be recreated separately — they are
intentionally not in this backup.

## Update — push (AUTHOR only)

On the author box, either let the plugin run automatically on session exit, or
run manually:

```bash
python C:\Users\bohen\hermes-backup\hermes_backup.py
```

The script, in order:

1. Whitelist-copies current state from `$HERMES_HOME` into `state/`.
2. Runs a secret-shape scan and **aborts before pushing** if any
   credential-looking value is found.
3. `git add -A` → commit → `git push -u origin main`, using a GitHub token read
   transiently from `$HERMES_HOME/.env` (never stored in the repo or in git
   config).

## Never in this repo

- `.env` and every API key / token (including the GitHub token itself)
- `auth.json` and other OAuth credential stores
- `state.db` / any sqlite database (the session store)
- `sessions/`, `logs/`, caches, images, audio
- private keys / certificates
- the `hermes-agent/` source tree

Before adding a new file to the backup, check it against this list plus the
whitelist and secret scan — do not assume it will (or should) sync.

## Invariants — do not violate

1. **One author.** Pushing from a second machine is what has previously
   diverged the branch and caused rejected pushes.
2. **Never commit secrets.** The scan is a safety net, not permission to relax
   the whitelist.
3. **Portable vs machine-local is fixed.** `config.yaml`, `gateway_state.json`,
   `channel_directory.json`, and the caches are machine-local by design — do
   not "improve" the consumer to deploy them.
4. **Prefer the scripts.** Both `hermes_backup.py` and `hermes_sync.sh` already
   resolve `$HERMES_HOME` per-OS and enforce the role split; do not hand-roll
   the sync.
