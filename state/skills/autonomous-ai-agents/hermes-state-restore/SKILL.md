---
name: hermes-state-restore
description: "Restore Hermes state from a backup repo or another machine."
version: 1.0.0
author: Hermes Agent (curator)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, restore, migration, backup, config, setup]
    related_skills: [hermes-agent, github-auth, hermes-state-backup]
---

# Hermes State Restore

Brings a configured Hermes (`config.yaml`, `SOUL.md`, `memories/`, `skills/`)
from a **backup repo or another machine** onto a target install, without
destroying the target's working secrets/runtime. This is the pull/restore
counterpart to the user's `hermes-state-backup` auto-push workflow (Windows box
pushes to a private GitHub repo; this Linux box pulls it back).

## When to use
- "Pull my hermes repo / configs" — user has a GitHub repo holding Hermes state.
- "Don't make me redo setup" — bring persona, memories, skills, and model aliases
  over from an existing install.
- A user hands you a `state/` directory mirroring `$HERMES_HOME` and wants it applied.

## Headless GitHub auth (private backup repos)
A backup repo is almost always **private**. `git clone` will prompt for a
password (the "could not read Username" failure = private repo; a bare `404`
via curl confirms it). `gh` may be installed but logged out. Do NOT paste a PAT
into chat. Use GitHub's device flow via `curl` (works headless, user finishes in
any browser/phone):

```bash
# 1. Request a device code. client_id is gh CLI's public one.
curl -s -X POST https://github.com/login/device/code \
  -H "Accept: application/json" \
  -d "client_id=178c6fc778ccc68e1d6a&scope=repo,workflow,read:org" | tee /tmp/gh_device.json
#  -> {device_code, user_code, verification_uri, expires_in, interval}

# 2. Show user: open verification_uri, enter user_code, approve.
# 3. Poll in background until authorized:
#    POST https://github.com/login/oauth/access_token
#    -d "client_id=...&device_code=<device_code>&grant_type=urn:ietf:params:oauth:grant-type:device_code"
#    response has access_token when approved.

# 4. Seed gh + git from the token:
TOKEN=$(python3 -c "import json;print(json.load(open('/tmp/gh_token.json'))['access_token'])")
echo "$TOKEN" | gh auth login --with-token
gh auth setup-git        # configures the git credential helper
gh api user --jq .login  # verify
```
Token lives in the system keyring — future git/gh ops won't prompt. See
`references/device-flow-authentication.md` for a full working transcript.

## Restore procedure (merge, don't overwrite)
1. **Clone** the repo: `git clone --depth 1 <url>` into `$HOME` and read its
   README/`.gitignore` — they document what the backup whitelists.
2. **Classify** the repo: `hermes_backup.py`-style mirrors usually contain
   `state/{config.yaml,SOUL.md,memories/,skills/,channel_directory.json,
   gateway_state.json,provider_models_cache.json,...}` and deliberately EXCLUDE
   secrets (`.env`, `auth.json`, `state.db`). If `.env` is present in the repo,
   warn the user — it shouldn't be there.
3. **Snapshot the target first**: copy current `config.yaml`, `SOUL.md`,
   `memories/`, `skills/`, `cron/` to a dated
   `/home/<user>/hermes-pre-restore-<ts>/`. Cheap insurance.
4. **Diff before touching**:
   - `diff <(cat backup/state/config.yaml) <(cat ~/.hermes/config.yaml)`
   - Compare `_config_version` in both — must match the installed binary's
     version (mismatch = migrate risk).
   - `SOUL.md`, `memories/*` — plain diffs; empty target dir = fresh install.
5. **Decide what to bring over** (the smart-merge rule set):
   - RESTORE: `SOUL.md`, `memories/MEMORY.md`+`USER.md`, and skills missing on
     the target (additive copy of whole skill dirs — never overwrite newer
     versions; preserve skills only the target has).
   - RESTORE config as DELTAS via `hermes config set KEY VAL` (never wholesale
     copy — hand-replacing `config.yaml` violates the "don't hand-edit config"
     invariant and can drop newer keys). Apply only meaningful user settings
     the target lacks (aliases, auxiliary.vision, etc.).
   - SKIP runtime/gateway files (`channel_directory.json`, `gateway_state.json`,
     caches) — they're machine-specific and overwriting a live gateway is risky.
   - SKIP entries that can't work on the target: plugins not installed (e.g.
     `hermes-backup` on non-Windows), MCP servers whose `${KEY}` has no `.env`
     value on the target, foreign platform channel configs.
6. **Verify**: `grep _config_version` unchanged (config not corrupted), skill
   count increased, new skills present, then `hermes doctor` (expect only
   pre-existing warnings: missing tokens for unused platforms, npm vulns).

## Pitfalls
- Don't `rm -rf` the target's `.env` or decrypt secrets from the repo — backups
  deliberately exclude them; re-point the target's existing `.env`.
- Blind wholesale `config.yaml` replace is a downgrade trap: the backup usually
  enables a backup plugin that isn't installed on the target and an MCP server
  with a placeholder `${...KEY}` that resolves to nothing. Merge the deltas
  instead.
- `hermes config set` writes clean YAML; after applying N settings re-check
  `_config_version` is unchanged and you didn't break the file.
- Cross-platform config objects copy fine even when tool sets add keys; missing
  newer keys are recomputed by Hermes at load — do not hand-merge them.

## Support files
- `references/device-flow-authentication.md` — full working device-flow curl
  transcript used to auth a private backup repo.