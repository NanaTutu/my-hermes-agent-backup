#!/usr/bin/env python
"""TCL/Google TV control for Hermes via the Cast (Chromecast) protocol.

Discovers a Cast device on the LAN (by name or host) and executes a control
command: status, volume (set/up/down), mute, media cast/play/pause/stop/seek,
and app launch (Netflix/YouTube/etc by app id).

Usage:
  python tcl_tv.py status [--name tutu] [--host 172.20.10.3]
  python tcl_tv.py volume 0.35            # 0..1
  python tcl_tv.py volume-up              # +5%
  python tcl_tv.py volume-down            # -5%
  python tcl_tv.py mute                   # toggle
  python tcl_tv.py cast URL
  python tcl_tv.py pause | play | stop
  python tcl_tv.py app netflix | youtube | ...   # launch a Cast app
"""
import argparse
import sys
import time

import pychromecast

DEFAULT_NAME = "tutu"
DEFAULT_HOST = "172.20.10.3"

# Well-known Cast app ids (TCL/Google TV)
APPS = {
    "youtube": "233637DE",
    "netflix": "CA5E8412",
    "prime": "A2A5E0CE",
    "spotify": "85D94702",
    "twitch": "4FCC00",
    "disneyplus": "9C77F7E7",
    "chromecast": "E8C28D4C",
}


def discover(name=DEFAULT_NAME, host=DEFAULT_HOST, timeout=8):
    cc, browser = pychromecast.get_chromecasts(timeout=timeout)
    dev = None
    for d in cc:
        if d.name.lower() == name.lower() or d.cast_info.host == host:
            dev = d
            break
    if dev is None:
        sys.exit(f"TCL TV not found (searched name={name!r} host={host!r}). "
                 "Is it powered on and on the same Wi-Fi/hotspot as this PC?")
    dev.wait(timeout=10)
    return dev


def cmd_status(dev):
    st = dev.status
    mc = dev.media_controller
    m = mc.status
    print(f"TV: {dev.name} ({dev.cast_info.model_name} @ {dev.cast_info.host})")
    print(f"  app active:    '{st.status_text}'")
    print(f"  volume:        {st.volume_level*100:.0f}% | muted: {st.volume_muted}")
    print(f"  media:         title={m.title!r} playing={m.player_state} "
          f"pos={m.current_time:.0f}s/{m.duration or '?'}s")


def cmd_volume(dev, value):
    dev.set_volume(value)
    time.sleep(1.5)
    print(dev.status.volume_level)


def cmd_volstep(dev, delta):
    cur = dev.status.volume_level
    nv = max(0.0, min(1.0, cur + delta))
    cmd_volume(dev, nv)


def cmd_mute(dev):
    dev.set_volume_muted(not dev.status.volume_muted)
    print(f"muted={dev.status.volume_muted}")


def cmd_cast(dev, url):
    dev.media_controller.play_media(url, "video/mp4")
    dev.media_controller.play()
    print(f"casting {url}")


def cmd_app(dev, app):
    if app not in APPS:
        # allow a raw app id too
        raise SystemExit(f"unknown app {app!r}; known: {list(APPS)}")
    dev.media_controller.blocking = False
    dev.launch_app(APPS[app])
    print(f"launched {app}")


# ---------------------------------------------------------------------------
# HDMI input switching via ADB (needs the TV's ADB debug bridge enabled)
# ---------------------------------------------------------------------------
ADB = r"C:\Users\bohen\AppData\Local\Android\Sdk\platform-tools\adb.exe"
TV = "172.20.10.3:5555"


def _sh(*args):
    import subprocess
    return subprocess.run(args, capture_output=True, text=True).stdout


def _adb(*args):
    return _sh(ADB, "-s", TV, *args)


def find_adb_focus():
    """Return (focus_index, [source_labels]) from the input-menu UI dump."""
    ui = _adb("shell", "uiautomator", "dump", "/data/local/tmp/_ui.xml")
    _adb("pull", "/data/local/tmp/_ui.xml", r"C:\Users\bohen\AppData\Local\Temp\tv_ui.xml")
    import os, re
    xml = None
    try:
        with open(r"C:\Users\bohen\AppData\Local\Temp\tv_ui.xml", encoding="utf-8",
                  errors="ignore") as fh:
            xml = fh.read()
    except FileNotFoundError:
        raise SystemExit("could not read uiautomator dump (menu open?)")
    labels, focus = [], None
    for m in re.finditer(
            r'text="([^"]+)"[^>]*?focused="(true|false)"[^>]*?selected="(true|false)"',
            xml):
        t = m.group(1).strip()
        if not t:
            continue
        labels.append(t)
        if m.group(2) == "true" or m.group(3) == "true":
            focus = len(labels) - 1
    return focus, labels


def cmd_switch_hdmi(target):
    """Open the input menu, DPAD-navigate to HDMI <target>, activate."""
    import time
    n = int(target)
    _adb("shell", "input", "keyevent", "3")     # HOME
    time.sleep(1.0)
    _adb("shell", "input", "keyevent", "178")   # open input menu
    time.sleep(2.0)
    for _ in range(3):
        focus, labels = find_adb_focus()
        if focus is not None and labels:
            break
        time.sleep(0.6)
    else:
        raise SystemExit("could not determine input menu focus")

    wanted = f"HDMI {n} (ARC)" if f"HDMI {n} (ARC)" in labels else f"HDMI {n}"
    if wanted not in labels:
        raise SystemExit(f"source {wanted!r} not in menu: {labels}")
    target_idx = labels.index(wanted)

    step = 1 if target_idx > focus else -1
    for _ in range(abs(target_idx - focus)):
        _adb("shell", "input", "keyevent", "22" if step > 0 else "21")  # RIGHT/LEFT
        time.sleep(0.5)
    _adb("shell", "input", "keyevent", "23")   # Center to activate
    time.sleep(2.5)
    print(f"switched to {wanted}")


# ---------------------------------------------------------------------------
# Wake-on-LAN (wake the TV from standby when "off" but still powered)
# ---------------------------------------------------------------------------
TV_MAC = "38:9b:73:5b:bc:0e"


def cmd_wake():
    """Send a Wake-on-LAN magic packet to the TV's MAC.

    Works when the TV is in standby (network interface still listening) and
    the PC is on the same LAN. Sends on UDP port 9 (and 7 as fallback).
    """
    import socket, struct
    mac_hex = TV_MAC.replace(":", "")
    if len(mac_hex) != 12:
        raise SystemExit(f"bad MAC: {TV_MAC}")
    magic = bytes.fromhex(mac_hex) * 16  # 6 x 0xFF + MAC x16
    magic = b"\xff" * 6 + magic
    host = DEFAULT_HOST
    sent = 0
    for port in (9, 7):
        for family in (socket.AF_INET,):
            try:
                s = socket.socket(family, socket.SOCK_DGRAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                s.sendto(magic, (host, port))
                sent += 1
                s.close()
            except OSError as e:
                print(f"  WOL send to {host}:{port} failed: {e}")
    print(f"WOL magic packet sent to {TV_MAC} @ {host} ({sent} targets)")
    return sent > 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=["status", "volume", "volume-up",
                                       "volume-down", "mute", "cast",
                                       "pause", "play", "stop", "app",
                                       "switch-hdmi", "wake"])
    p.add_argument("value", nargs="?", default=None)
    p.add_argument("--name", default=DEFAULT_NAME)
    p.add_argument("--host", default=DEFAULT_HOST)
    a = p.parse_args()

    dev = discover(a.name, a.host) if a.command not in ("switch-hdmi", "wake") else None
    if a.command == "status":
        dev = discover(a.name, a.host)
        cmd_status(dev)
    elif a.command == "switch-hdmi":
        cmd_switch_hdmi(a.value)
    elif a.command == "wake":
        cmd_wake()
    elif a.command == "volume":
        cmd_volume(dev, float(a.value))
    elif a.command == "volume-up":
        cmd_volstep(dev, 0.05)
    elif a.command == "volume-down":
        cmd_volstep(dev, -0.05)
    elif a.command == "mute":
        cmd_mute(dev)
    elif a.command == "cast":
        cmd_cast(dev, a.value)
    elif a.command == "app":
        cmd_app(dev, a.value)
    elif a.command in ("pause", "play", "stop"):
        mc = dev.media_controller
        getattr(mc, a.command if a.command != "play" else "play")()
        print(a.command)

if __name__ == "__main__":
    main()