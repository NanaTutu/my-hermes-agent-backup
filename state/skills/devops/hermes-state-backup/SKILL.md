---
name: hermes-state-backup
description: Set up or inspect Hermes state backups to GitHub.
---

# Hermes State Backup

Automate a private, secrets-safe backup of Hermes configuration state to a
user-owned GitHub repo, triggered on session exit. This mirrors the reference
setup at `C:\Users\bohen\hermes-backup\` (script) + the user plugin at
`~/.hermes/plugins/hermes-backup/`.

## Architecture

1. **Backup script** (`hermes_backup.py`) — whitelist-copies safe state into a
   local git mirror, runs a secret-shape scan, commits + pushes.
2. **On-exit trigger** — a user plugin registers an `on_session_finalize` hook
   that detached-launches the script.

## Trigger event

- `on_session_finalize` fires at CLI exit / session boundary (`cli.py`
  `_notify_session_boundary` → `lifecycle.finalize_session` →
  `plugins.invoke_hook`). This is the right event — fires once per real exit.
- `on_session_end` fires on EVERY turn (too noisy for a backup).

## Secret safety model (defense in depth)

- **Whitelist scope** — only safe paths mirrored: config.yaml, SOUL.md,
  memories/, skills/, cron/jobs.json, channel/gateway state, context caches.
- **Forbid list** — `.env`, auth.json, state.db, sessions/, logs/, caches,
  *.key/*.pem, curator internals, lock files. Match path segments AND full
  relpaths (`is_forbidden`).
- **Shape scanner** (`scan_for_secrets`) — abort before push if ANY staged file
  matches a credential *shape*: private keys, JWT, `sk-*` (incl. `sk-proj-*`),
  `ghp_*`/`github_pat_*`, AWS `AKIA`, Google `AIza`. Placeholder-shaped values
  (`your_key_here`, `sk-xxx...`, `resolve_api_key(...)`) are allowed.
- **Token hygiene** — GITHUB_TOKEN read from `$HERMES_HOME/.env` at runtime,
  used only transiently in the push header; never in git, config, or hooks.

## Pitfalls (learned the hard way)

- **MIRROR is read from env at import time.** To dry-run against a temp dir,
  set `HERMES_BACKUP_MIRROR` BEFORE importing the script (not inside a
  function) or module-level `MIRROR` won't reflect it.
- **gitignore unanchored patterns shadow nested dirs.** `hermes-agent/` (no
  leading `/<`) also ignored `state/skills/.../hermes-agent/`. Anchor to root:
  `/hermes-agent/`.
- **first-hit-per-file:** `scan_for_secrets` returns the first shape match per
  file (breaks after flag). Verify each secret form in separate files.
- **hermes config set can't build list-of-dicts** (the `hooks:` block) and
  `hermes hooks` has no `add` subcommand. Prefer a user plugin over hand-editing
  config.yaml (never hand-edit config.yaml).
- `plugins.enabled` gates loading; enable with `hermes plugins enable <name>`.
  Plugin takes effect next session.
- `hermes hooks test <event>` only exercises SHELL hooks, not plugin hooks.
  Validate a plugin hook with a real one-shot `hermes chat -q "..." --exit`.

## On-exit user plugin template

`~/.hermes/plugins/<name>/plugin.yaml`:
```yaml
name: <name>
version: 1.0.0
description: "..."
hooks:
  - on_session_finalize
```
`~/.hermes/plugins/<name>/__init__.py`:
```python
import os, subprocess
from pathlib import Path
VENV = Path(r"...\hermes-agent\venv\Scripts\python.exe")
SCRIPT = Path(r"...\hermes_backup.py")
DETACHED = 0x00000008 | 0x00000200 | 0x08000000  # DETACHED+NEW_GROUP+NO_WINDOW
def _run(**kw):
    try:
        with open(r"...\backup.log", "a") as lg:
            subprocess.Popen([str(VENV), str(SCRIPT)],
                             stdout=lg, stderr=subprocess.STDOUT,
                             creationflags=DETACHED)
    except Exception as e:
        ...
def register(ctx): ctx.register_hook("on_session_finalize", _run)
```

## Custom data/verification

Ad-hoc verify (tempfile, OS-safe): compile, secret scanner catches synthetic
creds, forbid allow/deny lists, `collect_source_files` clean, dry-run to temp
mirror asserting staged tree has no forbidden/secrets. Env for dry-run:
`HERMES_BACKUP_MIRROR` (not STAGING).

## Telegram notifications

`hermes_backup.py` sends a Telegram update via `hermes send --to telegram`
(no running gateway required) on two outcomes: successful push (commit+files)
and PUSH FAILED (error snippet). Silent on no-op runs — no noise each session.
`notify_telegram()` resolves `hermes.exe` next to `sys.executable` in the venv
Scripts dir; failure to notify never fails the backup (logged warn only).
Test: `hermes_backup.py` after any real change should produce a TG message with
`message_id` (verify with `hermes send --json`).

## Linux / macOS adaptation (installed on Tutu's Linux box)

The script + plugin are cross-platform as of the 2026-08-06 commit. Key deltas:

- **HERMES_HOME default** is platform-aware in `hermes_backup.py`:
  `~/.hermes` on Unix, `AppData/Local/hermes` on Windows. `MIRROR` default:
  `~/my-hermes-agent-backup` on Unix (the cloned repo), `~/hermes-backup` on
  Windows. Both still overridable via `HERMES_HOME` / `HERMES_BACKUP_MIRROR`.
- **Plugin launch** (`~/.hermes/plugins/hermes-backup/__init__.py`) uses
  `subprocess.Popen(..., start_new_session=True)` instead of Windows
  DETACHED flags, and passes `env` with `HERMES_HOME` + `HERMES_BACKUP_MIRROR`
  set explicitly. Logs to `<mirror>/backup.log` (gitignored via `*.log`).
- **`notify_telegram`** resolves the hermes binary: `hermes.exe` next to
  sys.executable (Win) → `hermes` next to it → `shutil.which("hermes")`
  (Unix). The Unix launcher lives at `~/.local/bin/hermes`.
- **GITHUB_TOKEN** must exist in `$HERMES_HOME/.env` — obtain with
  `gh auth token` (never print it; append the line, chmod 600 .env).
- **Hook validation**: `hermes chat --exit` DOES NOT EXIST. Use
  `hermes chat -q "just say OK" -Q`; the plugin fires `on_session_finalize`
  on exit and the detached script writes to `backup.log`.
- Expect a one-time config.yaml normalization commit right after
  `hermes plugins enable hermes-backup` (hermes rewrites config on next
  load); subsequent runs are silent no-ops ("no changes since last push").