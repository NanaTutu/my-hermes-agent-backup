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
  label"*. Recovery: kill the lingering `cua-driver.exe` worker PIDs
    (`taskkill /F /PID <n>`; the gateway-owned parent is often access-denied —
    that's expected), then call `computer_use(action="list_apps")` — that
    actually respawns a fresh session and a new cua-driver PID. A capture fired
    immediately after the kill can still fail with the same end-session error;
    use `list_apps` to re-initialize, then re-capture. (Do not push `capture`
    through the "this session has ended" loop twice — call `list_apps`.)
    Occasionally `list_apps` returns an empty `[ ]` list instead of respawning —
    in that case plain re-`capture` (narrowed to the app, e.g. `app="Chrome"`)
    after the kill also successfully regains a usable session; the end-session
    error is transient once the orphaned workers are gone.

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