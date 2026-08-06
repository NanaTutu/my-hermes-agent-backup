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