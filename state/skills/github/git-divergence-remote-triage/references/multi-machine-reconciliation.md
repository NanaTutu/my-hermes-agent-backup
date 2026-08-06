# Multi-machine repo reconciliation — concrete recipe

Worked example from reconciling `github.com/NanaTutu/my-hermes-agent-backup.git`
after two Hermes installs pushed to the same branch.

## Symptom
`git push origin main` rejected:
```
! [rejected] main -> main (fetch first)
```
with the hint "remote contains work that you do not have locally." This is a
history divergence, NOT a network/auth failure.

## Diagnosis sequence actually used (in order)
```
git remote -v                     # => HTTPS remote -> SSH probe irrelevant
curl -sS -o /dev/null -w "%{http_code}" https://github.com        # 200
curl -sS -o /dev/null -w "%{http_code}" https://api.github.com    # 200
git fetch origin                  # succeeded => creds fine; divergence confirmed
git log --oneline --graph HEAD origin/main
git rev-list --count e7e6086..HEAD          # local-only commits
git rev-list --count e7e6086..origin/main   # remote-only commits
git log --format='%h %an <%ae> %ad | %s' HEAD origin/main
git diff --stat origin/main HEAD            # 56 files changed => real content fork
```

## Identity tell
- Local:      `Hermes Backup Bot <backup@hermes.local>` — this machine's backup
  bot; hermes_home `C:\Users\bohen\...`.
- Secondary:  `Tutu <benohene8@gmail.com>` (the user), hermes_home
  `/home/tutu/.hermes` — this is the LINUX box, whose own backup plugin also
  pushed. Two identities + two different absolute paths = two devices.

## Reconciliation worked
```
git merge --no-commit --no-ff origin/main
git diff --name-only --diff-filter=U      # 2 files: state/gateway_state.json,
                                          # state/channel_directory.json
git checkout --ours -- state/gateway_state.json    # keep WINDOWS gateway (pid 46260)
git add state/gateway_state.json state/channel_directory.json
git commit --no-edit                        # merge commit c1e46b0
GIT_TERMINAL_PROMPT=0 timeout 60 git push origin main
git status -sb                              # "## main...origin/main" in sync
```

## Lasting architecture fix
The Linux Hermes was also running its backup-push on session finalize, into the
same repo. The durable fix is topology: keep the push side on ONE machine
(Windows bot); on the Linux box disable its backup-push plugin and pull instead
(`git pull`). Otherwise the two sides keep forking and next push rejects again.

## Verification script pattern
Write a temp script (never committed):
- `json.loads()` each resolved runtime JSON file, assert parse works
- assert no `<<<<<<<` / `=======` / `>>>>>>>` markers remain
- assert expected structure (e.g. `pid` + `gateway_state` for gateway_state.json)
- run `git status --branch` and require no ahead/behind
- remove the temp file afterwards.