---
name: windows-git-bash-workflows
description: "Windows git-bash workflows: servers, python, curl, paths."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [windows, git-bash, msys, terminal, node, python, curl, path-mangling, servers]
    related_skills: [windows-desktop-automation, kotlin-mobile-development]
---

# Windows Git-Bash Dev Workflows (Hermes terminal)

## Overview

Driving development workflows (Node servers, Python scripts, curl smoke tests) through the
Hermes `terminal` tool on Tutu's Windows box. The shell is git-bash/MSYS: POSIX syntax, but
Windows-native binaries underneath, which is exactly where the sharp edges live. This skill
captures the FIXES and patterns that work — verified on 2026-08-11 during the GhaLingo
contract-freeze smoke test — so future sessions don't re-derive them.

**Mindset:** these are host quirks with workarounds, not refusals. If a quirk stops
reproducing (tool updated, shell changed), prefer the native path and drop the workaround.

## Trigger Conditions

- Starting/stopping a Node/Express server and probing it with curl from the Hermes terminal.
- Running Python scripts that touch files while bash is involved.
- Building curl requests that send binary bodies (`--data-binary @-` or `@file`).
- Any `Unable to open file`, `can't open file 'C:\c\...'`, or silent process exit 1 in bash.

## Verified Pitfalls and Fixes

### 1. Hermes `terminal` background=true does not launch node on this host

Observed: `background=true` with `node dist/server.cjs` (or even `node -e "console.log(1)"`)
exits 1 instantly with zero node output — only bash "no job control / stdin is not a tty"
noise. Foreground node works fine. Not yet root-caused (PATH/env quirk in the runner's
non-interactive shell).

**Fix — wrapper-script pattern (proven):** write a small `.sh` that starts the server
internally with `&`, sleeps, curls, then kills. Run THAT script in the foreground:

```bash
# run-smoke.sh (run with: bash run-smoke.sh)
NODE_ENV=production node dist/server.cjs > /tmp/srv.log 2>&1 &
SERVER_PID=$!
sleep 3
bash scripts/contract-smoke.sh
RC=$?
kill $SERVER_PID 2>/dev/null
exit $RC
```

A reusable template lives at `scripts/drive-server-smoke.sh` in this skill. If
`background=true` starts working for node in future, prefer it (it is the cleaner tool);
the wrapper is the fallback that is known-good today.

### 2. MSYS path mangling: `/c/Users/...` fails when handed to Windows binaries

Observed: `python /c/Users/bohen/AppData/Local/Temp/script.py` → python receives
`C:\c\Users\...` and dies with "can't open file". MSYS converts the leading `/c/` only in
some contexts; direct argument passing to native binaries is unreliable.

**Fixes (either):**
- `cd /c/Users/...` FIRST, then reference the bare filename: `cd /c/Users/bohen/AppData/Local/Temp && python script.py`.
- Pass a NATIVE Windows path with forward slashes as the argument: `python "C:/Users/bohen/script.py"` works cleanly — it is the MSYS `/c/Users/...` form that gets double-converted to `C:\c\Users\...`.
- Avoid filesystem handoff entirely: pipe data via stdin (`python gen.py | curl --data-binary @- ...`).

### 3. Windows Python cannot write to MSYS `/tmp`

MSYS `/tmp` maps to a Windows temp dir that native Python does not resolve. Heredoc'd files
to `/tmp/x` silently fail (or write nowhere).

**Fix:** use paths relative to cwd, or skip files and pipe (see #2). `$TMPDIR`/`$(pwd)` are
safe; literal `/tmp/...` arguments are not.

### 4. `search_files` regex alternations return 0 matches on CRLF repos

Observed repeatedly on GhaLingo (CRLF line endings): `app\.(get|post|put|patch|delete)\(`
→ 0 matches, while plain single-term patterns (`express.json`, `app.use`) hit fine.

**Fix:** search with single plain-string patterns (no alternation groups) and iterate;
the tool's regex handling is unreliable with `|` groups on CRLF files.

### 5. `python` is uv-managed on this box (cpython 3.11), `pip` absent

Use stdlib-only scripts; don't assume `pip install` works without `uv` or a venv.

## Headless console subprocesses (Windows Python)

Spawning a console app (`hermes serve`, `python server.py`, `node`) as a
subprocess and wanting NO visible terminal window is a classic trap:

- **CREATE_NO_WINDOW is IGNORED when combined with DETACHED_PROCESS** (OS
  documented), AND CPython 3.11 does NOT translate CREATE_NO_WINDOW into a
  hidden STARTUPINFO window (it only does that with `shell=True`). So
  `DETACHED_PROCESS | CREATE_NO_WINDOW` still pops a console.
- **Correct combo: `CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW`** — drop
  DETACHED_PROCESS entirely. DETACHED_PROCESS alone allocates a FRESH console
  (visible window); CREATE_NO_WINDOW alone gives no console at all.
- **Verify empirically, don't trust the flag docs:** have the child print
  `ctypes.windll.kernel32.GetConsoleWindow()` (0 = no console). Measured on
  this host: inherit / DETACHED / DETACHED|NEW_GROUP / DETACHED|NEW_GROUP|NO_WINDOW
  all give hwnd != 0 (window); NEW_GROUP|NO_WINDOW and NO_WINDOW-only give hwnd 0.
- `CREATE_NO_WINDOW` is on `subprocess` itself (3.7+): `subprocess.CREATE_NO_WINDOW`.

Full flag matrix + reproduction + kill/relaunch recipe:
`references/headless-subprocess-and-respawn.md`.

## Diagnosing a process that "keeps reopening" on Windows

A window that respawns after you close it = an autostart entry + a watchdog
loop, not a crash. Trace the chain:

1. Find the process AND its parent — the parent is what relaunches it:
   `powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { \$_.CommandLine -match '<needle>' } | Select ProcessId,ParentProcessId,Name,CommandLine | Format-List"`.
2. Check the three autostart homes: Startup folder (user + common), registry
   Run/RunOnce keys, and `schtasks //query //fo LIST //v`.
3. A wrapper that `Popen`s a child + a `while True: sleep(30); restart-if-down`
   watchdog = the respawn loop. **Kill the WRAPPER (watchdog) FIRST, then the
   child** — otherwise the watchdog repopulates it within one interval.

## Binary Body Smoke-Test Pattern

Testing an endpoint that expects raw bytes (e.g. chunked uploads):

```bash
# Generate a valid WAV-ish payload and pipe it straight into curl:
python -c "
import struct, math, sys
sr = 16000; n = 4000
hdr = struct.pack('<4sI4s4sIHHIIHH4sI', b'RIFF', 36+n*2, b'WAVE', b'fmt ', 16, 1, 1, sr, sr*2, 2, 16, b'data', n*2)
sys.stdout.buffer.write(hdr + b''.join(struct.pack('<h', int(20000*math.sin(2*math.pi*440*t/sr))) for t in range(n)))
" | curl -s -X POST "$BASE/uploads/chunk?upload_id=$UID&chunk_index=1" \
    -H "Content-Type: application/octet-stream" \
    -H "Authorization: Bearer $TOKEN" --data-binary @-
```

Verify the server actually parsed the bytes (not mock fallback): response should echo
computed fields like `sampleRate`, `channels`, `file_size_bytes` matching your payload.

## Pitfall: file-based handoff inside smoke scripts

`$(pwd)/file.bin` inside a bash script can still reach Windows Python as `/c/...` — when in
doubt, always pipe (the `| curl --data-binary @-` form removes the file entirely). Never
write smoke artifacts into the repo tree; gitignore `uploads/`-style runtime dirs or delete
them after the run.

## Verification of this skill's advice

- Wrapper-script + foreground run: exit 0, full contract chain passed (register → missions
  → uploads/start → raw chunks ×2 → complete → sync).
- Piping bytes: server recorded `file_size_bytes: 16044` (44-byte header + 16,000 sample
  bytes) with `sampleRate: 16000` — real parse, not mock.
- `cd`-first python runs: exit 0.

## Related Skills

- `windows-desktop-automation` — GUI/browser automation (screenshots, clicks); this skill
  covers TERMINAL workflows, not the desktop surface.
- `kotlin-mobile-development` — GhaLingo Android project; its `references/ghalingo.md`
  points at this skill from its "Windows Host Quirks" section once adopted.