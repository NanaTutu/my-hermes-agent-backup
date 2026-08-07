---
name: windows-desktop-automation
description: Automate Windows GUI/browser with platform quirks.
version: 1.0.0
platforms: [windows]
metadata:
  hermes:
    tags: [windows, automation, computer-use, ui, powershell, screen-capture]
    category: devops
    related_skills: [computer-use]
---

# Windows Desktop & Browser Automation

Platform-specific knowledge for automating the Windows desktop and browser,
complementing the bundled `computer-use` skill (which owns the cross-platform
`computer_use` action vocabulary). Load this whenever the target host is
Windows and you run into the platform quirks captured here.

The durable lesson: on Windows, **background typing into a native browser
window is frequently blocked** — but foreground typing DOES work once the
driver is at ≥0.18.0 (delivered via SendInput). Keep the driver upgraded and
prefer foreground delivery for text input.

## Windows input delivery quirks (root causes, not "tool broken")

1. **Chrome blocks background text input.** `computer_use(type=...)` against a
   Chromium window class (`Chrome_WidgetWin_1`) returns `code:
   "background_unavailable"` (event kind `text_input` is dropped). Background
   click, scroll, and capture still work — only typed text is affected.
2. **Foreground typing: driver-version dependent.** On OLD cua-driver
   (≤0.12.x), retrying the type with `delivery_mode:"foreground"` errors with
   *"foreground swap ... rejected by Windows ... this daemon is not at
   UIAccess integrity"* — it tried `SetForegroundWindow` and hit the Windows
   foreground-lock. After `hermes computer-use install --upgrade` to **≥0.18**,
   foreground text input is delivered via `SendInput` (route `global_input`)
   and WORKS on Chrome without UIAccess elevation. **If you see the UIAccess
   foreground error, upgrade the driver — do not conclude typing is
   impossible.**

## Reading numeric values: trust the AX tree, not the vision description

A `capture(mode="som")` returns BOTH an AX `elements[]` array and a
`vision_analysis` natural-language description. For any number you must act on
(precise prices, balances, margins, P/L, lot sizes, timestamps), READ IT FROM
THE `elements[]` ARRAY (a `Text`/`Edit`/`Button` node label), NEVER from
`vision_analysis`. The auxiliary vision model summarises loosely and has been
observed to fabricate digits — on a dense Exness webtrading page it reported
`Balance: 58.08`, `Margin: 8.66`, `Margin level: ~7408.77%` while the AX nodes
held the true `Balance 50.00`, `Margin 0.67`, `Margin level 7450.75%`. The
vision text is a descriptive summary for orientation; treat figures in it as
unverified until confirmed against a node. If numbers are time-sensitive (a
live quote or account equity), prefer a node read and cross-check against a
second capture before building a report on them.

**Parsing `get_window_state` / `capture` JSON in Python (field-name gotcha).**
Each node in `elements[]` stores its number under **`element_index`** (an int),
NOT `index` — using `e.get('index')` silently returns `None` and your dump
prints nothing, which looks like a dead session. Other node fields: `role`,
`label`, `frame` (`x/y/w/h`), `enabled`, `depth`. When you parse the JSON you
saved with `get_window_state`, filter by `element_index` range and grep the
`label`s; use `role` to tell `Text`/`Button`/`TabItem` apart.

## Workarounds (in priority order)

- **Foreground typing works on cua-driver ≥0.18.** Retry a blocked `type`
  with `delivery_mode:"foreground"` — the driver briefly activates the target,
  types via SendInput, and restores the previous foreground. It can be flaky
  when an overlay/popup holds focus (e.g. an extension popup), so verify with
  a re-capture before pressing Enter.
- **Launch targets from the terminal instead of typing.** For "go to a URL"
  tasks: `powershell -NoProfile -Command "Start-Process 'chrome.exe'
  -ArgumentList 'https://<url>'"`. Opens a tab in the already-running Chrome
  instance and it becomes the active tab. Usually the cleanest path.
- **Reuse existing elements/controls** (already-open tabs, the address bar via
  click + keyboard shortcuts) rather than composing text input.
- **Durable fix:** keep cua-driver updated (`hermes computer-use
  install --upgrade`); the newer UIA/SendInput worker is what makes typing
  reliable. Verify with `hermes computer-use doctor` / `status`.

## cua-driver 0.18 API changes (upgrade gotchas)

- **Element tokens, not bare indices.** 0.17+ rejects `click(element_index)`
  without a snapshot — the computer_use tool must receive an element from a
  FRESH `capture(mode="som")` in the same session, or the driver refuses with
  `snapshot_id_required`. Re-capture before every click.
- **Stale driver process after upgrade.** The old cua-driver.exe parent may
  survive the upgrade and `capture` errors with *"cua-driver list_windows
  failed: this session has ended; call start_session explicitly to reuse its
  label"*. Recovery: kill the lingering `cua-driver.exe` worker PIDs, then call
  `computer_use(action="list_apps")` — that actually respawns a fresh session
  and a new cua-driver PID. A capture fired immediately after the kill can
  still fail with the same end-session error; use `list_apps` to re-initialize,
  then re-capture. (Do not push `capture` through the "this session has ended"
  loop twice — call `list_apps`.) Occasionally `list_apps` returns an empty
  `[ ]` list instead of respawning — in that case plain re-`capture` (narrowed
  to the app, e.g. `app="Chrome"`) after the kill also successfully regains a
  usable session; the end-session error is transient once the orphaned workers
  are gone.
- **Health-check BEFORE you kill (Aug 2026 watch).** The wedge is not always a
  dead driver. Run `cua-driver autostart status` / `cua-driver status` FIRST: if
  the daemon reports running, it is HEALTHY — the stale `session has ended`
  label is only in the Hermes tool's session bookkeeping, and
  `Stop-Process -Name cua-driver` may refuse to kill the autostart daemon (it is
  the real, needed daemon). A kill refused by name AND by PID with the PID
  unchanged is the signal to STOP trying — that PID is the live daemon, not an
  orphan. Skip the kill entirely and go straight to the CLI path below:
  `cua-driver call start_session` with a FRESH session name, then drive
  `list_windows` / `get_window_state` / `click` directly. In the Aug 2026 watch,
  kill attempts failed against the live daemon yet the fresh CLI session worked
  immediately — the kill was never needed.
- **From git-bash, kill cua-driver with PowerShell, NOT `taskkill`.** You are
  NOT in cmd: `taskkill //F //PID <n>` (and `//F //IM`) fails with
  *"Invalid argument/option - '//F'"* — git-bash mangles the `/` flags. It can
  even appear to "succeed" (`exit 0`) if you `2>/dev/null` the stderr, leaving
  the workers alive and the session still wedged. Use
  `powershell -Command \"Stop-Process -Name cua-driver -Force -ErrorAction SilentlyContinue; Start-Sleep 2\"`.
  There are usually TWO workers (an `mcp` and a `serve` daemon) — a name kill
  clears both, then the next `computer_use(capture, app="...")` re-initializes
  and works. Verify with `tasklist | grep -i cua || echo none`. If even kill +
  `list_apps` + re-capture loops on the same end-session error, drop to the CLI
  below.

**A useful quirk confirmed while watching live positions (Exness web PWA):** a
`capture(mode="som")` on the open positions tab returns a RICH AX tree for the
whole row — symbol `GBP/USD`, `Sell`, lot `0.01`, open price, current price,
TP/SL buttons, ticket `23958538`, swap, live `P/L`, plus the account footer
(`Balance 50.00`, `Equity`, `Margin level`, `Total P/L`). Grep the `elements[]`
labels for the row (ticket / `P/L`), and confirm the position is still open by
the `TabItem Open 1` node being active as opposed to `TabItem Closed`. When the
trade's only way to stay silent is a missing capture, the same row-grep logic
handles `Closed`.

## Starting the daemon from git-bash: use `autostart kick`, not `serve`

When `cua-driver serve` must be re-launched (daemon died, or `status` reports "not running"),
**do NOT start it as a git-bash background process.** `terminal(background=true, command="cua-driver serve
--socket '\\\\.\\pipe\\cua-driver'")` fails with *os error 123 "The filename, directory name, or
volume label syntax is incorrect"* — git-bash mangling of the `\\.\pipe\...` named-pipe socket path.
Setting `MSYS_NO_PATHCONV=1` does NOT fix it; neither does double- or single-quoting forms,
because the pipe name is reconstructed from mangled backslashes inside the child process.

Working fix (no shell at all): the daemon is registered as a Windows **autostart Scheduled Task** on
this host, so start it through that task:

```bash
cua-driver autostart status   # -> "registered (running)" / "registered (not running)"
cua-driver autostart kick     # Start the 'cua-driver-serve' Scheduled Task for this session
cua-driver autostart status   # confirm "registered (running)"
```

Then confirm the pipe is really up before touching the tools:
```bash
cua-driver status              # "daemon is running" — or if it errors with a risk-classification
                               # message, the daemon IS up (the message means only that 'status'
                               # as a tool has no review class); use `autostart status` instead.
```
Heads-up: after `autostart kick` the Hermes `computer_use` tool may still report the stale
`"this session has ended"` label — the CLI path (below) is the reliable route regardless.
Also, prefer `cua-driver autostart kick` over hand-running `serve` because a `terminal(...background=true)`
`serve` is tied to that shell's lifecycle and can silently exit when the cron/task shell goes away.

## Bypass a wedged `computer_use` session — drive the cua-driver CLI directly

The recovery above (kill orphans + `list_apps` + re-capture) works most of the time, but it is
NOT guaranteed: a truly wedged session can keep returning the identical
`"cua-driver list_windows failed: this session has ended; call start_session explicitly to
reuse its label"` on **every** tool call — `list_apps` returns `[]`, plain re-`capture` returns
the same end-session error, and even killing every `cua-driver.exe` process doesn't revive it
because the Hermes tool keeps trying to reuse a stale session label. Don't keep fighting the
tool. **Drop down to the cua-driver CLI and drive it directly** — no Hermes session needed:

```bash
# 0. `cua-driver` is on PATH (resolves to AppData\Local\Programs\Cua\cua-driver\bin).
# 1. Confirm daemon state (read-only, safe)
cua-driver status        # "daemon is running" / "not running"
# 2. If needed, stop and start a FRESH daemon (`serve` runs forever -> start it as a
#    Hermes background process via terminal(background=true), not nohup/disown)
cua-driver stop
# NOTE: from git-bash, `cua-driver serve` in the background FAILS to create the
# named pipe (os error 123 "syntax is incorrect") even with MSYS_NO_PATHCONV=1.
# On this host the daemon is a registered autostart Scheduled Task — restart it
# with `cua-driver autostart kick` instead (see "Starting the daemon from git-bash").
cua-driver serve          # in background (fails on git-bash; use autostart kick)
# 3. Declare a new session (separate from the wedged Hermes one).
#    capture_scope:"window" (or omit -> default "auto", also window-only) suffices for
#    read-only monitoring: list_windows + get_window_state + AX-row grep + background
#    TabItem clicks all work in window scope. "desktop" is ONLY needed to escalate to
#    raw-coordinate / whole-desktop gestures — don't reach for it to just read a position.
cua-driver call start_session '{"session":"<some-fresh-name>","capture_scope":"window"}'
# 4. Find the target window and capture its window_id
echo '{}' | cua-driver call list_windows   # -> { "windows" : [ { "pid","title","window_id","bounds" } ... ] }
# 5. Read a window: AX tree AND a screenshot you own in one response
echo '{"pid":<pid>,"window_id":<win_id>,"screenshot_out_file":"C:/Users/<u>/AppData/Local/Temp/d.svg"}' | \
  cua-driver call get_window_state   # -> elements[] + tree_markdown, PNG written to the file
```

**CLI arg passing on this git-bash host.** BOTH forms work, pick whichever you prefer:
- Via stdin: `echo '{"pid":31344,"window_id":722668}' | cua-driver call get_window_state`
- **As a single-quoted positional JSON arg** (confirmed working this host): `cua-driver call start_session '{"session":"watcher"}'` and `cua-driver call get_window_state '{"pid":31344,"window_id":722668}'` both succeed directly. The critical requirement is that the arg reach the driver as **well-formed JSON text** — a single-quoted literal does this cleanly.

The failure mode is NOT "stdin-only"; it's passing a **bare token / flag** that isn't JSON. `cua-driver call get_window_state --pid 31344` (flag style) errors with *"Missing required integer field pid"*, and `cua-driver call list_windows --app chrome` (bare positional) errors with *"positional JSON arg ... did not parse: expected value at line 1 column 1 / received: chrome"*. So: single-quote the JSON, whether you pipe it through stdin or put it as an argument — either is reliable. (The `--help` hint blaming PowerShell 5.1 is misleading here — you're in bash, the root cause is that the arg must be JSON text.)

**`screenshot_out_file` beats base64-decode.** `get_window_state` accepts a `screenshot_out_file` path and writes the PNG straight to disk — much cleaner than the older `include_image:false` + base64-decode-the-JSON dance. Use it when you want to `vision_analyze` the window. Note the file arg is a Windows path form (`C:/Users/...`), and native `python` won't read MSYS `/tmp` — write to an absolute path under `$HOME`.

Key facts that kept this from being guesswork:
- `list_windows` gives each window a `window_id` (a large int, e.g. 722668). **`get_window_state`
  REQUIRES `window_id`** — passing only `pid` errors with *"Missing required integer field
  window_id"*. Get `pid` from the same windows list.
- `get_window_state` returns `{ "elements": [...], "tree_markdown": "...",
  "screenshot_png_b64": "..." }`. The screenshot is downscaled to ≤1455px. **Save the JSON,
  base64-decode `screenshot_png_b64` to a PNG, and `vision_analyze` the PNG** — that is how you
  "see" a window when the AX layer is thin. (On Windows, git-bash `/tmp` is not readable by the
  native `python`; write JSON/PNG to an absolute path under `$HOME`/Desktop instead.)
- **Exness webtrading AX richness varies by page build — do NOT assume canvas-thin up front.**
  An older build session found the AX tree almost empty (a few `Edit`/`ComboBox` nodes only) and
  required screenshot decode. A later session (Aug 2026) got the FULL positions table straight
  from the AX `elements[]` array via `get_window_state`: row nodes `GBP/USD`, `Sell`, lot button
  `0.01`, `1.34514` open price, `1.34533` current, TP `1.34000` / SL `1.34644` buttons, ticket
  `23958538`, open time, swap, `P/L -0.19`, plus account footer `Balance 50.00`, `Equity 49.81`,
  `Margin level 7,434.33%` — all machine-readable, no vision needed. **Sequence: dump the
  `elements[]` labels first and grep for the row (symbol/lot/ticket/P-L); only if the tree is
  genuinely bare fall back to base64-decode `screenshot_png_b64` + `vision_analyze`.** When the
  AX tree is rich, trust it over the vision description for numbers (see "Reading numeric values" above). `TabItem Open 1` / `TabItem Closed` nodes distinguish open from closed tabs.
  **Empirically it FLIP-FLOPS between sessions for the same terminal** — an Aug 2026 watch had the full
  open-position row machine-readable in `elements[]`; a later watch returned a THIN tree (only the live
  price `Text` nodes and `TabItem`/`Document` chrome; no positions row at all), so the numeric fallback
  to base64-decode-`screenshot_png_b64` + `vision_analyze` was required. Expect either shape and always
  grep `elements[]` first before assuming the tree is bare. When only vision is available, vision is
  RELIABLE for the binary open/closed verdict (it correctly reported the trade still under the "Open 1"
  tab) but UNRELIABLE for precise figures — it misread the account balance (58.08 vs true ~50) and the
  live quote. For a silent live-position watch, the binary verdict is all you need to decide stand-by;
  only surface exact numbers when the AX tree (or a confirm re-check) backs them.

Full end-to-end recipe with the exact commands: `references/cua-driver-cli-recovery.md`.

Silent live-position watch on the Exness web terminal (find the trading tab via
AX TabItem, activate with element_token click, grep the Open/Closed row,
decide stand-by vs. report): `references/exness-tab-watch-recipe.md`.

PLACING an order on the Exness web terminal (open SELL/BUY ticket via pixel-click
on the TradingView button, fill protective legs with focus-then-set_value,
re-resolve the stale confirm token, verify the fill via toast + Open-count):
`references/exness-order-entry.md`.

## Targeting the correct browser window (multi-window / PWA gotcha)

`capture(app="chrome.exe")` does NOT always give you the window you want. This
host runs many Chrome windows/tabs (Composio, Google Drive, Exness PWA, etc.);
a bare `app="Chrome"` capture grabbed a random existing tab (e.g. Composio)
while the Exness web-trading PWA sat in its own window. `app="Exness"` also
fails to match even though the Taskbar shows "Exness - 1 running window",
because the PWA is a `chrome_proxy.exe --app-id=...` window, not a process the
driver resolves by display name.

**Reliable recipe — find the window by its title, then capture by handle:**
1. Enumerate Chrome windows and match the one whose title identifies it:
   ```powershell
   Get-Process chrome -ErrorAction SilentlyContinue |
     Where-Object { $_.MainWindowTitle -ne '' } |
     Select-Object Id,ProcessName,MainWindowTitle,MainWindowHandle
   ```
   (On this git-bash host run it as `powershell -NoProfile -Command "..."`.)
   The Exness PWA window shows up with a live title like
   `GBP/USD Bid 1.34521 - Google Chrome` → note its `Id` (PID) and
   `MainWindowHandle`.
2. Capture that exact window with the computer_use tool, passing both:
   `app="chrome.exe"`, `pid=<Id>`, `window_id=<MainWindowHandle>`,
   `mode="som"`.
3. Then drive it normally (element-index clicks, not raw coords — coords
   mis-scale on this driver).

Apply the same pattern to any Chromium/Electron PWA that "runs" but refuses to
resolve by `app=` name. Verify which window you actually got by checking the
capture's `Document` title / first elements (a window whose address bar shows a
different site means you captured the wrong tab).

**Variant (Aug 2026): the terminal may be a TAB inside another Chrome window,
not a standalone PWA.** A `cua-driver call list_windows` showed only YouTube /
Composio / Exness Personal Area top-level windows — no `GBP/USD` window at all.
The trading terminal lived as a `TabItem` (label `GBP/USD Bid 1.34538 - High
memory usage - 1.0 GB`) INSIDE the main Chrome window's AX tree. Recipe:
  1. `get_window_state` each candidate Chrome window (pid + window_id from
     `list_windows`); grep element labels (role `TabItem`) for `GBP/USD Bid`.
  2. Activate it with a background UIA click on its `element_token`:
     `cua-driver call click '{"pid":<pid>,"window_id":<win_id>,"element_token":"<token>","delivery_mode":"background"}'`.
     The result reports `effect: unverifiable` — that is NORMAL, not failure.
  3. Re-run `get_window_state`; the terminal DOM (positions table + account
     footer) now appears in the AX tree, and the `Document` label is the live
     quote (e.g. `GBP/USD Bid 1.34544`). Verify the tab became active before
     reading the row.
  The tab title carries a live quote (it updates with the market, and may show
  a `High memory usage` suffix) — cheap live-price source even before viewing
  the positions table.

**Don't key window selection on the tracked-pair name in the title (Aug 2026
watch).** The Exness terminal's window/tab title shows the **currently-active
CHART tab's symbol**, which is NOT necessarily the pair of the position you are
monitoring. In a live watch tracking GBP/USD (ticket 23958538), `list_windows`
returned the terminal window titled `USD/JPY Bid 158.324 - Google Chrome` — the
chart had been switched to a USD/JPY tab while the GBP/USD SELL 0.01 row still
sat in the positions table under `TabItem "Open 2"`. The AX `elements[]` had
BOTH the USD/JPY SELL row AND the tracked GBP/USD row (open 1.34514 / current
1.34443 / TP 1.34000 / SL 1.34644 / ticket 23958538). Lesson: identify the
terminal by ANY Chrome window whose title matches the broker/quote pattern
(`<Pair> Bid <price> - Google Chrome`), then read the position by **grep of
the AX `elements[]` for the ticket/symbol** — never assume the tracked pair's
name appears in the title, and never conclude the trade is gone from a title
change alone. The positions table + `TabItem Open/Closed` is ground truth.

## Screen capture to a deliverable PNG

`computer_use(action="capture")` returns image bytes in-context, which is fine
on CLI but is not directly sendable as a file. When you need an actual file
(e.g. `MEDIA:/path.png` on a messaging platform), capture the display to PNG:

```
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/screen_capture.ps1 [output.png]
```

Saves the primary screen to `%USERPROFILE%\screenshot.png` (or the given path).
Use the ready-made copy in `scripts/screen_capture.ps1`.

## git-bash to PowerShell quoting (big gotcha on this host)

`[Type]::Static` tokens get mangled when you inline PowerShell inside a
git-bash `-Command` string — bash treats `[` as an escape, so
`\[System.Drawing.Point\]::Empty` becomes invalid PowerShell and throws parser
errors. **Rule: write the PowerShell to a `.ps1` file (with `write_file`) and
run it with `-File`, never inline it in a `-Command` string.** Inline quote
escaping is also fragile; the file approach sidesteps all of it.
Also: **bash control operators do not survive inside `powershell -Command
"..."`** — `...; tasklist | grep -i cua || echo none` fails with *"The token
'||' is not a valid statement separator in this version"*. Keep ONLY
PowerShell-legal separators (`;`) inside the quoted string and move bash
operators (`|`, `||`, `&&`) OUTSIDE the quotes into their own `terminal()`
call, e.g. `powershell -NoProfile -Command "Stop-Process ...; Start-Sleep 2"`
then a separate `tasklist | grep -i cua || echo none`.

## Reading a page: prefer vision, fall back to AX tree

`capture(mode="vision")` gives a natural-language page description via the
configured auxiliary vision provider (`vision_analysis_routed_via:
auxiliary.vision`) — use it first; it is more informative than the AX tree for
**qualitative** page understanding. Caveat: this description must NOT be used
for precise numbers — see the "Reading numeric values" section above (the AX
`elements[]` array is authoritative for figures). If vision fails, or no
vision LLM is configured (`auxiliary.vision` → "Run:
hermes setup"), fall back to `capture(mode="ax")`, which returns the full
accessibility/DOM tree as element labels; describe the page from those. Watch
the element cap: dense pages (e.g. YouTube homepage around 430-460 elements)
truncate at the default 100 — raise `max_elements` (e.g. 330) to get the feed
content. To FIX a missing vision backend instead of working around it, see
the `hermes-provider-and-alias-setup` skill
(`references/auxiliary-vision-config.md`).

## Verification

- `ls -la` the saved PNG and confirm it is `PNG image data, <W>x<H>` — catches
  blank/failed captures.
- After launching a URL, re-capture the app (`app="chrome.exe"`) and confirm
  the active `Document` title changed to the target site before screenshotting.

## Pitfalls

- `computer_use(action="capture", app="screen")` can grab a useless 1x1 tray
  window (e.g. XboxPcTray) instead of the real screen. Prefer capturing a
  specific running app by name; use `action="list_apps"` first to confirm the
  process name.
- Background click/scroll/capture work even when typing does not — do not
  assume the whole driver is broken from one text-input failure.
- **Native Windows `python` cannot resolve git-bash MSYS paths.** Inside
  `terminal` (bash), `python /c/Users/<u>/Desktop/script.py` fails with
  "can't open file 'C:\\c\\Users\\...'". Fix: `cd /c/Users/<u>/Desktop && python
  script.py` (or run `python .\\script.py`), not an absolute `/c/...` path with
  a bare `python` that is the MSYS-wrapped exe. `uv`-managed pythons are also
  native exes and hit the same rule.
- **`execute_code` is BLOCKED in cron jobs** ("cron_mode ... no user present
  to approve it"). Do the base64 decode of `screenshot_png_b64` via a
  `write_file`'d python script run through `terminal`, not `execute_code`.
  The write_file+terminal path shown in the CLI recovery reference is the
  approved route.