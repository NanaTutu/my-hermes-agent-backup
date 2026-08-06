# Hermes State Backup

Private backup of **Tutu's Hermes agent configuration state**, excluding all
secrets and credentials.

## Auto-trigger

A user plugin at `C:\Users\bohen\AppData\Local\hermes\plugins\hermes-backup\`
registers an `on_session_finalize` hook (fires on every Hermes session exit).
It launches `hermes_backup.py` as a detached background process, logging to
`backup.log` in this directory. Verify with:

    hermes plugins list --user --plain

## What is backed up

The `state/` directory mirrors a strict **whitelist** of re-creatable,
non-sensitive Hermes state:

- `config.yaml` — settings (never credentials)
- `SOUL.md` — agent persona
- `memories/` — durable memory + user profile (markdown only)
- `skills/` — installed skills (no curator backups / usage db)
- `cron/jobs.json` — scheduled job definitions
- `channel_directory.json`, `gateway_state.json`
- `context_length_cache.yaml`, `provider_models_cache.json`

## What is NEVER backed up

Secrets, credentials, PII, and runtime artifacts are excluded by a whitelist
+ hard-forbid list, then verified by a secret-shape scan before commit:

- `.env` (all API keys / tokens, including the GitHub token itself)
- `auth.json` / OAuth credential stores
- `state.db` and all `*.db` / sqlite files (session store)
- `sessions/`, `logs/`, caches, images, audio
- private keys / certificates
- the `hermes-agent/` source tree

The secret scan looks for credential *shapes* (OpenAI/GitHub/Slack/AWS/Google
keys, JWTs, private-key blocks) and aborts the push if anything suspicious is
found — never committing it.

## How to run manually

```bash
python C:\Users\bohen\hermes-backup\hermes_backup.py
```

The GitHub token is read from `$HERMES_HOME/.env` at push time and sent as an
ephemeral Authorization header. It is never stored in this repo or in git
config.

## How it runs automatically

A Hermes shell hook fires on the `on_session_finalize` event (session close) to
run this same script, so the backup stays current after each session.

## Two-machine model (single writer)

This repo is the **single writer / many readers** config pipeline for Tutu's two
Hermes installs:

- **Windows box = AUTHOR.** Builds/edits skills and SOUL here; the
  `on_session_finalize` backup plugin (Hermes Backup Bot identity) is the *only*
  thing that pushes new commits to this repo.
- **Linux box = CONSUMER.** Mirrors this Windows config. On it, `hermes_sync.sh`
  auto-detects the CONSUMER role, so it never pushes back — it pulls (ff-only)
  and deploys the portable snapshot:

```bash
# inside the Linux clone (~/my-hermes-agent-backup), after cloning:
./hermes_sync.sh
```

`hermes_sync.sh` refreshes the snapshot, then copies the **portable** trees —
`SOUL.md`, `skills/`, `memories/`, `cron/` — into `$HERMES_HOME`
(`~/.hermes` on Unix). It deliberately does **not** touch machine-local files
(`config.yaml`, `gateway_state.json`, `channel_directory.json`, the caches);
those stay per-machine because they encode local paths, API identity, routing
and process state that legitimately differ between boxes.

## Deploy on any Hermes agent (OS-aware)

`hermes_sync.sh` is the **single entry point** for this repo. Drop the clone on
any Hermes box and run it — the script auto-detects the OS, picks the box's
role, and acts accordingly, so you never have to reconfigure per machine:

```
+----------------+---------------------------+------------------------------------+
| OS             | role (auto)               | what it does                        |
+----------------+---------------------------+------------------------------------+
| Windows        | AUTHOR (single writer)   | runs hermes_backup.py -> git PUSH   |
| Linux/macOS/BSD| CONSUMER (reader)        | pulls ff-only + deploys portable   |
+----------------+---------------------------+------------------------------------+
```

Concretely:

```bash
./hermes_sync.sh                          # pick role by OS
HERMES_ROLE=consumer ./hermes_sync.sh     # force reader (e.g. a shared headless box)
HERMES_ROLE=author   ./hermes_sync.sh     # force writer (e.g. a second authoring box)
```

Rules of thumb:

- **Keep exactly one AUTHOR.** The Windows box is the designated one. Pushing
  from more than one box is what previously diverged the branch and caused
  rejected pushes. If you add another authoring machine, you take over manual
  conflict-handling on repo.
- **CONSUMER never pushes.** It refreshes the snapshot and copies only the
  portable trees (`SOUL.md`, `skills/`, `memories/`, `cron/`) into
  `$HERMES_HOME` (`~/.hermes` on Unix, `%LOCALAPPDATA%\hermes` on Windows).
  It deliberately skips machine-local files — `config.yaml`,
  `gateway_state.json`, `channel_directory.json`, the caches — because those
  encode local paths/API identity/routing and must stay per-box.
- **Auto-run on the AUTHOR** is wired via the `hermes-backup` plugin's
  `on_session_finalize` hook (fires each session close). On a CONSUMER, hook
  `hermes_sync.sh` to a scheduled job / login so it re-syncs periodically.

`hermes_backup.py` and `hermes_sync.sh` each already resolve `$HERMES_HOME` by
OS (`~/.hermes` on Unix, `%LOCALAPPDATA%\hermes` on Windows), so they behave
correctly on either kind of box.

## Restore

Check out `state/` from this repo and copy the files back into your
`$HERMES_HOME`. Secrets (`auth.json`, `.env`) must be recreated separately —
they are intentionally not in this backup.