---
name: tcl-tv-cast-control
description: Control Tutu's TCL Google TV via Cast from Hermes.
version: 1.0.0
platforms: [windows]
metadata:
  hermes:
    tags: [smart-home, cast, chromecast, tcl, tv, pychromecast]
    category: smart-home
---

# TCL TV Cast Control

Control Tutu's TCL Google TV (`tutu` @ `172.20.10.3`) as a smart-home device
over the LAN Cast (Chromecast) protocol. Bi-directionally verified working
(Aug 2026): read volume/status AND drive volume/mute/cast/apps from Hermes.

## Environment (prebuilt)

- Python env with pychromecast: `C:\Users\bohen\castenv\Scripts\python.exe`
  (created via `uv venv castenv` + `uv pip install --python 'C:\Users\bohen\castenv\Scripts\python.exe' pychromecast`).
- Control CLI: `C:\Users\bohen\AppData\Local\hermes\scripts\tcl_tv.py`

Calling convention that WORKS on this git-bash host (MSYS path mangling breaks
MSYS-style `/c/...` args; use native Windows path form):

```bash
P='C:\Users\bohen\castenv\Scripts\python.exe'
S='C:\Users\bohen\AppData\Local\hermes\scripts\tcl_tv.py'
"$P" "$S" status
"$P" "$S" volume 0.35        # set 0..1
"$P" "$S" volume-up          # +5%
"$P" "$S" volume-down        # -5%
"$P" "$S" mute               # toggle
"$P" "$S" cast https://...   # cast a video URL
"$P" "$S" app netflix        # NOTE: this Cast launch command is broken (launch_app missing in this pychromecast); use ADB instead:
"$A" -s $H shell am start -n com.netflix.ninja/.MainActivity   # verified launch (package is com.netflix.ninja, NOT com.netflix.ninja.tv)
"$A" -s $H shell monkey -p com.netflix.ninja -c android.intent.category.LAUNCHER 1   # alternative; returns 252 if package missing
"$P" "$S" pause | play | stop
"$P" "$S" switch-hdmi 2      # switch TV input to HDMI 2 (ADB; works from any state)
```

## HDMI input switching (via ADB — added Aug 2026, verified

`switch-hdmi <N>` opens the input menu, reads the *currently selected source*
from the uiautomator dump, DPAD-navigates to `HDMI N`, then hits Center.
Works from any current source. Verified round-trip HDMI 1 ↔ HDMI 2.

Key gotchas (all hit and solved):
- Do NOT use `input tap` on the tile — it only sets a visual *hover*, and a
  subsequent OK press activates whatever has DPAD focus (often Home), silently
  closing the menu without switching. Use genuine DPAD navigation
  (RIGHT=22 / LEFT=21 / CENTER=23).
- The input menu is a TCL overlay (`com.tcl.suspension`); focus is exposed as
  `selected="true"/"false"`, NOT `focused`. A regex expecting digits
  `focused="(\d+)"` silently matches nothing.
- Auto-switch verification: after the switch, `dumpsys activity activities`;
  `topResumedActivity` should be
  `com.google.android.tv.inputplayer/.player.PassthroughPlayerActivity`.
- During HDMI passthrough, `screencap` returns a 0-byte file (external signal
  bypasses the compositor) — that's EXPECTED, evidence of passthrough, not error.

## Discovery (one-off, then rely on the CLI)

```bash
'C:\Users\bohen\castenv\Scripts\python.exe' - <<'EOF'
import pychromecast
cc, browser = pychromecast.get_chromecasts(timeout=8)
for d in cc: print(d.name, d.cast_info.model_name, d.cast_info.host)
EOF
```

Notes: `get_chromecasts` returns a `(devices, browser)` TUPLE — unpack both.
Use `dev.wait(timeout=10)` before reading `dev.status` (status is None until
the connection negotiates). device has no `.host` attr; use `d.cast_info.host`.

## Network

- TV: TCL "Smart TV", friendly name `tutu`, UUID dcfaee33..., host 172.20.10.3,
  cast port 8009 (cast_type `cast`).
- It lives on an iPhone personal-hotspot LAN `172.20.10.0/28` (PC = .2,
  gateway = .1 DNS-only, TV = .3). Cast discovery REQUIRES the TV and PC on
  the SAME network. If it stops responding, first confirm PC + TV are on the
  same Wi-Fi, then verify with a port scan for 8008/8009/8443.

## ADB (full remote control) — ENABLED Aug 2026

The TV also runs the Android ADB bridge (TCL G13_2K_GB build). This unlocks
full remote control: key presses, app launching, reading the on-screen app,
and screencap (I can SEE the TV).

- ADB client: `C:\Users\bohen\AppData\Local\Android\Sdk\platform-tools\adb.exe`
  (v36). Server: `adb -s 172.20.10.3:5555 ...`
- First-time: `adb connect 172.20.10.3:5555` → TV shows "Allow USB debugging?"
  prompt → user ticks "Always allow from this computer" → re-connect.
  Authorization persists (RSA key in ~/.android).
- One-time TV-side setup: Settings → System → About → tap **Build Number**
  7× → Settings → System → Developer options → **USB debugging ON**.

Verified commands (all tested live):
```bash
A='C:\Users\bohen\AppData\Local\Android\Sdk\platform-tools\adb.exe'
H=172.20.10.3:5555
"$A" -s $H connect $H                              # connect
"$A" -s $H shell input keyevent 3                  # HOME
"$A" -s $H shell input keyevent 4                  # BACK
"$A" -s $H shell dumpsys activity activities | grep topResumedActivity   # what's on screen
"$A" -s $H shell dumpsys tv_input | grep -i hdmi   # HDMI input map (2 HDMI ports, both connected)
"$A" -s $H exec-out screencap -p > tv.png          # screenshot the TV (1280x720)
```
Keyevent codes: 3=HOME, 4=BACK, 19/20/21/22=DPAD up/down/left/right, 23=OK,
85=PLAY/PAUSE, 86=STOP, 24/25=volume up/down, 26=power.

Source question ("what input is the TV on?"): Cast API does NOT expose HDMI
source. Use ADB: `topResumedActivity` tells the foreground app
(`com.google.android.apps.tv.launcherx` = Google TV home; `tv.settings` =
settings; an HDMI input shows as `com.mediatek.tvinput` component). HDMI
hardware map via `dumpsys tv_input` (type=9 = HDMI, hdmi_port 1/2,
cable_connection_status=1 = cable connected).

## Pitfalls

- **MSYS path mangling:** do NOT pass `/c/Users/...` as a script arg to a
  python exe from git-bash — it becomes `C:\c\Users\...`. Use native
  `C:\Users\...` Windows paths.
- `get_chromecasts` returns a tuple; callers that treat it as a list get
  `'list' object has no attribute 'name'`.
- `volume-up`/`volume-down` are incremental (+/-5%); `volume <0..1>` sets
  absolute.

## Verification

- `status` prints `TV: tutu (Smart TV @ 172.20.10.3)` and a volume%.
- After any set, re-read status and confirm the value actually changed
  (read-back check) before reporting success.