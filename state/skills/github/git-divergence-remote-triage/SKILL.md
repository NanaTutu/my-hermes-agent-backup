---
name: git-divergence-remote-triage
description: Triage a GitHub remote check or fetch-first push rejection.
---

# Git Remote & Divergence Triage

Use when the user asks to "check the remote connection to GitHub", push is
rejected as non-fast-forward, or a repo has stray commits you "never made".
Frames the actual failure correctly before doing anything destructive.

## Rule 1 — Establish the REAL transport before probing
- `git remote -v` tells you SSH vs HTTPS. If HTTPS, an `ssh -T git@github.com`
  probe is IRRELEVANT — a `Host key verification failed` there does not mean
  the HTTPS remote is broken. Don't chase it.
- Reachability: `curl -sS -o /dev/null -w "%{http_code}" https://github.com`
  and the same for `https://api.github.com`. Expect 200. This separates
  "network down" from "auth problem" from "history problem".
- Auth/diagnose: `git credential fill` and bare `git ls-remote` can HANG
  (exit 124) non-interactively when Git Credential Manager (`credential.helper
  = manager`) is waiting on a GUI/browser prompt. A hang is not "bad creds".
- Decisive pulse check: run the real operation with
  `GIT_TERMINAL_PROMPT=0 timeout 60 git fetch origin`. A successful fetch/push
  proves the remote + stored token both work. Do this LAST; it's the truth.

## Rule 2 — divergence triage (reject "fetch first")
A push rejection that says the remote "contains work you do not have" means
the branch diverged, not that you can't reach GitHub.

1. `timeout 60 git fetch origin` (needed to see what the remote actually has).
2. `git log --oneline --graph HEAD origin/main` to see the fork point.
3. `git rev-list --count <fork>..HEAD` and `..origin/main` — how many on each side.
4. **Who authored the mystery commits?** `git log --format='%h %an <%ae> %ad | %s'`
   against local HEAD and each remote-only SHA. A private repo with two
   identities means a SECOND machine (or a backup bot with a different git
   identity) pushed there. Match identity + paths against your own machines
   before assuming data loss.
5. `git diff --stat <remote_tip> HEAD` — content genuinely divergent, or just
   timestamps? Runtime/state files diverging between two machines is expected;
   shared config/skill diverging is a real fork.

## Rule 3 — reconcile the merge safely
- `git merge --no-commit --no-ff origin/main` — preview, don't force.
- Conflicts: `git diff --name-only --diff-filter=U`.
- Machine-local runtime artifacts (PIDs, absolute paths, per-host channel/
  gateway state) conflict on EVERY sync between two machines. Resolve with THIS
  machine's values: `git checkout --ours -- <file>` then `git add`. These
  should arguably be excluded from the shared repo entirely.
- Rebase is NOT the default — it rewrites history on a repo with a second
  writer and can silently drop the other side. Use a merge commit instead.
- After merge + push, confirm convergence: `git status -sb` shows no ahead/
  behind.

## Rule 4 — stop recurrence: one pusher, one puller
When two machines both auto-push backup to the SAME repo, one will eventually
build on a stale base and reject. The real fix is topology, not the merge: one
box (the AUTHOR) pushes; every other box (CONSUMER) disables its push daemon and
merely `git pull`s. Any automated "reconciliation" script that pushes from the
non-author box will just re-fork.

### Concrete single-writer deployment for Hermes state
- The author runs the backup push plugin (`hermes_backup.py`, backup-bot
  identity). The consumer box clones the repo and lets the AUTHOR own the ref.
- The consumer does NOT push. It refreshes the snapshot and deploys only the
  PORTABLE trees into its live home. A ready-made script ships as
  `templates/hermes_sync.sh` in this skill. It is now an **OS-aware role
  dispatcher**, not just a consumer puller:
  - Detects OS via `uname`: Windows (MINGW/MSYS/CYGWIN) -> AUTHOR; any POSIX
    (Linux/macOS/BSD) -> CONSUMER. Override with `HERMES_ROLE=author|consumer`.
  - AUTHOR role invokes `hermes_backup.py` (the push backend); CONSUMER role
    does `git pull --ff-only origin` then rsync/cp SOUL.md, skills/, memories/,
    cron/ into `$HERMES_HOME` (`~/.hermes` on Unix, `%LOCALAPPDATA%\hermes` on
    Windows), leaving machine-local files untouched.
  - Purpose: drop the repo on ANY box, run `./hermes_sync.sh`, and it "knows
    what to do" by OS — no per-machine role config. Document this in the repo
    README alongside the ASCII OS->role table.
- Split every synced state dir into PORTABLE (SOUL.md, skills/, memories/,
  cron/) vs MACHINE-LOCAL (config.yaml, gateway_state.json,
  channel_directory.json, caches). Portable gets copied cross-machine;
  machine-local never does. This is the durable lesson: `git pull` is not
  deploy — you still need a copy step to a per-machine home.

Full worked example with the real command sequence used: see
`references/multi-machine-reconciliation.md`.

## Verification
Ad-hoc script (temp, os-safe): read each resolved file, `json.loads` it, assert
NO `<<<<<<<`/`=======`/`>>>>>>>` markers remain, assert expected structure;
then `git status --branch` shows `main...origin/main` (in sync).

## Pitfalls
- Reading `git credential fill` exit 124 as "auth broken" is a false negative;
  GCM just needs an interactive session.
- `ssh -T git@github.com` failure on an HTTPS remote wastes the whole triage.
- Blanket `git pull --rebase` / `git reset --hard origin/main` after a rejection
  can drop content. Understand, then decide.
- Runtime JSON `gateway_state.json` / `channel_directory.json` are per-machine
  — always resolve to the LOCAL machine's values, never the remote's.
- **`#!/usr/bin/env python3` shebang breaks on Windows/MSYS.** The MINGW bash
  shell usually exposes `python` but NOT `python3`, so invoking a `.py` script
  directly yields `env: 'python3': Permission denied`. When a dispatcher script
  must run a Python backend cross-platform, probe for an interpreter
  (`for cand in ${HERMES_PYTHON:-} python3 python`) and call it explicitly
  rather than relying on the shebang.
- **Native Windows Python misreads MSYS paths.** Passing `/c/Users/...` to a
  native `python.exe` yields a bogus `C:\c\Users\...` target ("can't open file").
  Convert with `cygpath -w` before invoking when `cygpath` exists, else leave
  the path as-is on real Unix.
- **A pipeline masks the real exit code.** `./script | tail -x` reports tail's
  status in `$?` — an exit-0 in the pipeline does not mean the script succeeded.
  Use `${PIPESTATUS[0]}` (bash) when the script is the first stage of a pipe.
- When testing role dispatch, beware the miscalibrated assertion: an AUTHOR box
  with fresh state is *meant* to commit+push, so asserting "no new commit" will
  fail by design. Test consumer idempotence separately (scratch HERMES_HOME)
  and assert the AUTHOR produced a push, not that it stayed put.