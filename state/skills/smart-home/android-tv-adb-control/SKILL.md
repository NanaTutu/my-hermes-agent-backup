---
name: android-tv-adb-control
description: Control Android TV via ADB. Use when driving the TV UI.
version: 1.0.0
platforms: [windows]
metadata:
  hermes:
    tags: [smart-home, android-tv, adb, tv, remote-control, google-tv]
    category: smart-home
---

# Android TV / Google TV control via ADB-over-network

Cast (Chromecast) can only control the *cast session* (volume, cast media,
launch cast apps). It CANNOT switch HDMI inputs, press the OS/remote buttons,
read the foreground app, or drive the TV UI. For that you need **ADB** over
the network. this skill covers the enable + connect + control workflow for any
Android-based TV/box (Android TV / Google TV). The user's specific instance
(TCL "tutu" @ 172.20.10.3) is in references/instance-tutu.md.

## When to reach for ADB instead of Cast
- "What source/input is the TV on?" or "switch to HDMI 2"
- Button presses (dpad / back / home / power) — NOTE: volume is the exception;
  on MediaTek/TCL builds ADB VOLUME keyevents often don't move the output
  level. Prefer the Cast layer (`set_volume` 0..1) for volume; keep ADB for
  everything else. See `references/instance-tutu.md` (Volume section).
- Reading the current foreground activity / apps
- Anything needing `dumpsys` / `pm` / deeper OS state

## Connect on the machine
- Android platform-tools from the Android SDK, NOT on PATH:
  `$HOME/AppData/Local/Android/Sdk/platform-tools/adb.exe`.
- Use native `$HOME/...` or `C:\Users\...` paths (MSYS `/c/...` mangled).

## One-time per TV
1. TV: Settings → System → About → tap **Build Number** 7×
   ("You are now a developer").
2. Settings → System → Developer options → enable **USB debugging** (usually
   opens ADB-over-network on TCP 5555). If 5555 stays closed, also enable
   "Wireless debugging" / "ADB over network".
3. Confirm the port is open BEFORE connecting:
   `python -c "import socket;s=socket.socket();s.settimeout(2);s.connect(('<IP>',5555));print('open')"`
4. `"$ADB" connect <IP>:5555` then `"$ADB" devices -l`.

First run: `adb server` auto-starts (tcp:5037) — normal. First `connect` often
prints `failed to authenticate` and lists the device as **unauthorized** — the
TV shows an on-screen "Allow USB debugging?" dialog; the human must tick
"Always allow from this computer" + OK. Re-run `adb devices -l`; it should now
list `device`. Every command errors with `device unauthorized` until approved.

## Once authorized
- Foreground activity / input state:
  `"$ADB" shell dumpsys activity activities | grep -i mResumedActivity`
- Home / switch source:
  `"$ADB" shell am start -a android.intent.action.MAIN -c android.intent.category.HOME`
- Key events: `"$ADB" shell input keyevent <CODE>`
  HOME=3, BACK=4, DPAD_UP=19/DOWN=20/LEFT=21/RIGHT=22, ENTER=66,
  VOLUME_UP=27 / VOLUME_DOWN=25, POWER=26.
- Full `dumpsys`, `pm`, etc. — deepest layer.

## Pitfalls
- ADB not on PATH — call `platform-tools/adb.exe` explicitly.
- MSYS path mangling applies to adb.exe too.
- Without on-screen approval the device stays `unauthorized`.
- If 5555 stays closed after dev-mode, enable Wireless debugging, re-scan.

## Advanced Android-TV ADB techniques — added Aug 2026
These came out of driving an Android TV / Google TV tuner + inputs over ADB:
- **Live input passthrough returns a 0-byte screencap** — on HDMI inputs AND
  the live television tuner (and while a channel-scan dialog renders), the
  active picture bypasses the compositor, so `screencap -p` comes back empty.
  That 0-byte is EXPECTED, not an error — read on-screen text via
  `uiautomator dump` + pull instead, and track state changes via
  `dumpsys activity activities | grep topResumedActivity`.
- **Wake-on-LAN reaches the network layer, not necessarily the screen.** Sending
  a WOL magic packet (MAC from `arp -a`) wakes the standby Wi-Fi interface
  (ping/ADB/Cast start answering, HDMI device handshakes resume) but on many
  Android TVs does NOT prove it alone brings the OS up. VERIFY HONESTLY: if the
  human had to press power, do not claim "WOL woke the TV."
- **Region finding:** `adb shell getprop persist.sys.country` reports the
  configured broadcast region (e.g. `GH`). Use it before blaming channel-scan
  failures on an unset region.
- **Tuner/antenna hardware present** when `dumpsys tv_input` lists
  `...tuner.*InputService` entries. Per-port `cable_connection_status=1`
  (CONNECTED) vs `2` (disconnected) tells whether an antenna/AV source is wired
  even when a scan finds 0 channels (signal-strength problem, not wiring).
- **Nested Android-TV menus are horizontal or vertical — check before pushing
  DPAD.** A "Channels" submenu that navs with RIGHT/LEFT will appear to
  "jump out" if you send DOWN. Read `uiautomator dump` node bounds to get the
  orientation and exact tap/DPAD targets rather than guessing direction.
  Deep tracks in one skill: instance-specific wins go in
  `references/instance-tutu.md` (see patch history for WOL + tuner-scan).

## Verification
- `adb devices -l` must show `device` (not `unauthorized`/`offline`).
- A `shell` command must return real output before claiming control works.