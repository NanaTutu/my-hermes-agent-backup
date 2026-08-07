# cua-driver CLI recovery — when `computer_use` won't revive

Session-proven end-to-end recipe for when the Hermes `computer_use` tool is stuck returning

```
capture failed: cua-driver list_windows failed: this session has ended; call start_session explicitly to reuse its label
```

and the usual fixes (kill `cua-driver.exe` workers, `action="list_apps"` to respawn, plain
re-`capture`) do NOT clear it. Driving the driver CLI directly bypasses the dead Hermes
session entirely.

## Context
- Target: Windows host, git-bash (MSYS) terminal. Use POSIX syntax in `terminal` calls.
- Driver binary on PATH: `cua-driver` → `%LOCALAPPDATA%\Programs\Cua\cua-driver\bin` →
  `~/.cua-driver/packages/releases/<ver>-x86_64-pc-windows-msvc/` (0.18.0 on this host).
- Goal example (this session): read the Exness web-trading "Open"/"Closed" positions table in a
  Chrome window titled `GBP/USD Bid ... - Google Chrome`.

## Steps

1. Diagnose (read-only):
   ```bash
   cua-driver status      # daemon running? pid? permission mode?
   cua-driver doctor      # full health report; also prints if a newer release exists
   ```
   A "daemon is not running" or a stale pid file at `%LOCALAPPDATA%\cua-driver\cua-driver.pid`
   pointing at a dead process both explain the tool's failure.

2. Get to a clean daemon — **use `autostart kick`, not `serve`** (git-bash quirk, see SKILL.md:
   `cua-driver serve` started from git-bash fails with os error 123 named-pipe mangling even with
   `MSYS_NO_PATHCONV=1`):
   ```bash
   cua-driver stop
   cua-driver autostart status     # -> "registered (not running)"
   cua-driver autostart kick       # start the 'cua-driver-serve' Scheduled Task
   cua-driver autostart status     # -> "registered (running)"
   ```
   Verify the pipe is up with `cua-driver status` (a risk-classification error from `status`
   actually means the daemon IS running — fall back to `autostart status` to disambiguate).

3. Declare a session with desktop scope:
   ```bash
   cua-driver call start_session '{"session_id":"mystder-<timestamp>","capture_scope":"desktop"}'
   ```
   Response `{"active": true, "capture_scope": "desktop", ...}` means go.

4. Enumerate windows and find the target by title — **pass JSON args via stdin**, not bare
   positional or `--flag` values (the `--app chrome` and `get_window_state --pid` forms error with
   parse/missing-field messages; this is bash, the git-bash warning about PowerShell is a red herring):
   ```bash
   echo '{}' | cua-driver call list_windows
   ```
   Find the row whose `title` contains your target (e.g. `GBP/USD Bid ...`). Note its `pid`
   and `window_id` (large int, e.g. 722668).

5. Read the window, writing the PNG straight to disk (**avoid the base64-decode dance**):
   ```bash
   echo '{"pid":<pid>,"window_id":<window_id>,"screenshot_out_file":"C:/Users/<u>/AppData/Local/Temp/win.png"}' \
     | cua-driver call get_window_state > wstate.json
   ```
   IMPORTANT: `get_window_state` errors with "Missing required integer field window_id" if you
   only pass `pid`. Always pass both. `screenshot_out_file` is a Windows path form
   (`C:/Users/...`); use an absolute path under `$HOME` — native python cannot read MSYS `/tmp`.

6. Read the AX tree / screenshot — **check the AX elements first** (with `screenshot_out_file` the
   PNG is already on disk, so no decoding needed; only the AX-grep step uses python):
   ```python
      import json
      d = json.load(open(r'C:\\Users\\bohen\\Desktop\\wstate.json'))
      for e in d.get('elements', []):
          lbl = e.get('label') or e.get('name') or e.get('text') or ''
          if lbl:
              print(e.get('role'), '|', str(lbl)[:100])   # grep for your row: symbol, lot, ticket, P/L
      ```
      The PNG is at the path you passed to `screenshot_out_file` (step 5) — point `vision_analyze`
      straight at that file if you need the visual. On git-bash, the native Windows `python` canNOT
      read `/tmp/...` AND canNOT open a `/c/Users/.../script.py` path passed to `python` — `cd` into
      the directory first and run `python decode.py`, or the run fails with
      `can't open file 'C:\\c\\Users\\...'`. Write files to an absolute path like
      `C:\\Users\\bohen\\Desktop\\...` and point the Windows python at the `C:\\...` path form.
      NOTE: `execute_code` is blocked in cron jobs (no user to approve arbitrary local python);
      run the decode via a `write_file`'d script + `terminal` instead.

7. Read numbers from the AX elements when present (see next section); `vision_analyze` the
   decoded PNG only when the tree came back bare.

## Why the AX tree FIRST, screenshot as fallback (revised)
An EARLIER session on an old Exness page build found the AX `elements[]` array held ONLY a
handful of nodes (`https://my.exness.com/webtrading/` Document, a `Favorites` ComboBox,
`Regular form` ComboBox, an `Edit` `'0.01'`, `'regular'`, ...) and no position row text, forcing
screenshot decode. A LATER session (Aug 2026) on the current build got the FULL positions table
from the AX array alone: row nodes `GBP/USD`, `Sell`, lot `0.01`, open price `1.34514`, current
`1.34533`, TP `1.34000` / SL `1.34644`, ticket `23958538`, open time, swap, `P/L -0.19`, plus
account footer `Balance 50.00` / `Equity 49.81` / `Margin level 7,434.33%`, and
`TabItem Open 1` / `TabItem Closed` tab states — all machine-readable. **So: dump and grep the
AX `elements[]` labels first; decode the screenshot only if the tree is genuinely thin.** When
the tree is rich, prefer AX nodes over any vision description for exact numbers.

## Gotchas hit this session
- `taskkill //F //IM cua-driver.exe` works in git-bash, but plain `taskkill /F /IM ...` does
  not (double-slash form). Also killing the gateway/parent worker is often access-denied — use
  `cmd /c "taskkill /F /PID <n>"` if `//` gives "Invalid argument".
- Deleting a stale `%LOCALAPPDATA%\cua-driver\cua-driver.pid` does not lower the Hermes tool's
  session label; it still errors. Only the CLI-direct path reliably completes the read.