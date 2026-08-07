# Instance — Tutu's TCL / Google TV "tutu"

Concrete values for the user's TV, for fast reuse.

## Device facts (verified Aug 2026)
- Friendly name: `tutu`
- Model: TCL "Smart TV" (Google TV / Android TV), build `G13_2K_GB`
- Host: `172.20.10.3` — Cast port 8009, ADB port 5555
- UUID (Cast): dcfaee33-2b5f-b477-3513-faf40f034468
- MAC (for Wake-on-LAN): `38:9b:73:5b:bc:0e` (from `arp -a`)
- Network: iPhone personal-hotspot LAN `172.20.10.0/28`
  — PC = 172.20.10.2, gateway = 172.20.10.1 (DNS-only), TV = 172.20.10.3.

## Quick connect (this device)
```bash
ADB="$HOME/AppData/Local/Android/Sdk/platform-tools/adb.exe"
python -c "import socket;s=socket.socket();s.settimeout(2);s.connect(('172.20.10.3',5555));print('port open')"
"$ADB" connect 172.20.10.3:5555
"$ADB" devices -l
```

## ADB session status at time of writing
- `adb connect 172.20.10.3:5555` succeeded; `adb server` auto-started (tcp:5037).
- Device listed as `unauthorized` on first try — the TV's "Allow USB
  debugging?" on-screen prompt was pending human approval ("Always allow from
  this computer" + OK). After approval, re-run `adb devices -l` and it should
  show `device`.
- Cast-layer control (volume/status) was fully verified working earlier in the
  same session — see the separate `tcl-tv-cast-control` skill for Cast; ADB
  is the layer to use for inputs/buttons/deep state.

## Known-good Cast facts (for completeness)
- pychromecast guest discovery: `get_chromecasts(timeout=8)` returns a TUPLE
  `(cc, browser)` — unpack both; `dev.wait(timeout=10)` before reading
  `.status`. Use `d.cast_info.host`, not `d.host`.
- Cast CANNOT see/switch HDMI input or press remote buttons — use ADB for that.

## HDMI switching (verified round-trip HDMI 1 ↔ 2)
- `tcl_tv.py switch-hdmi <N>`: opens the input menu, reads the currently
  selected source from `uiautomator dump`, DPAD-navigates, hits Center.
- Always DPAD (RIGHT=22/LEFT=21/CENTER=23), NOT `input tap` — tap only sets a
  visual hover; an OK press then activates the DPAD-focus target (often Home).
  TODO no tabs. The input menu is `com.tcl.suspension` overlay; selection is
  exposed as `selected="true"` (NOT `focused`).
- Post-switch confirm: `dumpsys activity` → topResumedActivity =
  `com.google.android.tv.inputplayer/.player.PassthroughPlayerActivity`.
  HDMI passthrough gives a 0-byte screencap (expected).

## Wake-on-LAN experiment (Aug 2026 — VERIFY HONESTLY)
- `wake` magic packet reaches the standby Wi-Fi chip: after WOL, the interface
  left powersave (mDNS answers, ping/lives again, HDMI device re-handshakes —
  you see the HDMI device "flicker"). Example of ripple: when TV awake was in
  standby, `ping` went no-reply → after WOL + time it became reachable.
- BUT a wake alone did NOT reliably turn the panel on this unit — the screen
  eventually came on after a human pressed power. Do NOT report "WOL woke the
  TV" unless you independently confirm power actually flipped via network.
  If the user says "I put it on," then THAT is who turned it on, not WOL.

## Free-to-air antenna / channel scan (Aug 2026 — scan now RUN end-to-end)
- TV has hardware A*/DVB tuner services: `com.mediatek.tvinput/.tuner.*`
  (Digital/Analog/Cable/Satellite) + HDMI + composite.
- Region already set to Ghana: `getprop persist.sys.country` = `GH`. If a scan
  finds 0, region is NOT the cause on this unit.
- `dumpsys tv_input`: per-port `cable_connection_status=1`=CONNECTED vs
  `2`=disconnected. Antenna/tuner sensors report 1 — an antenna wired shows as
  CONNECTED even when a scan finds 0 channels (weak signal, not wiring).
- Channel scan (verified end-to-end, 2026-08-07): MENU(82) → the **Channels
  submenu is HORIZONTAL tabs** (Programme guide · Channel up · Channel down ·
  Channel · Channel management) — navigate RIGHT/LEFT (22/21), NOT down; DOWN
  jumps out of the bar. Chain that worked:
  1. `keyevent 82` (MENU) → focus lands on **Source**
  2. `keyevent 19` (UP) → lands on **Programme guide** (Channels submenu open)
  3. `keyevent 22` (RIGHT) → **Channel up** (the tab bar will NOT step past
     Channel up via DPAD — taps are what open further)
  4. `keyevent 23` (OK) → tuning config screen: Channels · Analogue · Antenna ·
     Cable · Satellite · Auto Channel Update · Channel Update Message
  5. `input tap` on **Antenna** row (~y=290) → expands to: Channel scan ·
     Update Scan · Single RF Scan · Channel scan type · Channel store type
  6. `input tap` on **Channel scan** (~y=205) → scan starts.
- Scan progress: `topResumedActivity` = `com.mediatek.wwtv.tvcenter/...ScanDialogActivity`
  for the WHOLE scan (several minutes). Screencap is 0-byte while it renders —
  read the dialog via `uiautomator dump` instead:
  `['Status: Scan completed', 'Antenna', 'Digital channels:  0', '100%', 'Finish']`.
  uiautomator dump can block during the scan — poll `dumpsys activity` with
  short ADB calls rather than long Python loops.
- Result (indoor antenna, Ghana): scan completed 100% but **Digital channels: 0**.
  logcat showed `[DVBT]P1_TPS Lock` during the scan → tuner locked a DVB-T
  carrier but found no channels → weak signal. Diagnosis: antenna electrically
  connected (status=1), tuner healthy, region set, DOA = signal strength ->
  user buys outdoor antenna, rescan after.
- Close the dialog: tap the **Finish** button (bounds from uiautomator dump,
  e.g. center ~(1172,632)); then `ScanDialogActivity` gone.
- "Channel management" appears greyed but is enabled=true in the a11y tree;
  the grey is a focus-rendering state. HOWEVER DPAD stops at "Channel" — the
  scan is NOT inside Channel management on this build; use the Antenna →
  Channel scan path above. (Channel management stays locked until ≥1 channel
  exists — it is a management/edit gate, not the scan entry.)

## Volume control — use CAST, not ADB keyevents (verified Aug 2026)
- On this TCL, `input keyevent 25/27` (VOLUME_DOWN/UP) do NOT change the
  actual output volume (stored `settings get system volume_music` stays put;
  live `dumpsys audio` shows a separate scale). Do not waste cycles on them.
- Authoritative path is the **Cast layer** (pychromecast): read via
  `tcl_tv.py status` (prints `volume: NN%`), set absolute with
  `tcl_tv.py volume <0..1>` (e.g. `volume 0.14` → 14%), or `volume-up/volume-down`
  (±5%). Always re-read `status` to confirm the read-back before reporting.
- `tcl_tv.py volume` REQUIRES a 0..1 float arg — calling it bare raises a
  `TypeError: float() argument ... NoneType`. Use `status` to read instead.
- If ADB reports `device ... not found` but `ping` + port-5555 scan succeed,
  the network is fine and only the ADB session dropped — just re-issue
  `adb connect 172.20.10.3:5555` (derives instantly) before the next shell call.

## Settings/tuner gotchas spotted
- DPAD in these nested MediaTek menus is easy to overshoot — verify selection
  with `uiautomator dump` after EACH press; use node `bounds` to tap targets
  exactly rather than guessing display coordinates.