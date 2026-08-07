---
name: wing-osc-console-control
description: "Use when controlling a Behringer WING console over OSC."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [behringer, wing, osc, console, mixing, audio]
    category: audio-engineering
---

# WING OSC Console Control

Drive a Behringer WING mixing console live over the network using its **OSC**
remote protocol (UDP **2223**; native remote = 2222). Discovery → probe →
read/write parameters (faders, mutes, EQ, buses) → recall scenes — from the
same PC that controls the user's TV.

Companion to the **behringer-mixer-scenes** skill: that one authors `.snap` /
`.scn` files offline; this one controls the desk live. Both use the same
parameter tree (`ae_data`).

## When to Use

- User asks to control a WING console on the network (fader/mute/EQ changes, reading channel state, identifying the desk).
- Sweep a LAN to find the console's IP.
- Verify the protocol works before pushing snapshot files to the desk.

**Don't use for**: authoring/validating `.snap` JSON files (that's `behringer-mixer-scenes`).

## Protocol facts (from the official WING OSC doc, P.-G. Maillot)

- **UDP port 2223** for OSC; 2222 = native binary remote. Replies go to the caller's port.
- **Probe**: send `/?` → reply string:
  `WING,<ip>,PGM,<model>,<serial>,<fw:build>` (e.g. `WING,192.168.1.71,PGM,ngc-full,NO_SERIAL,1.07.2-40-g1b1b292b:develop`)
- **Tree walk**: `/` returns the first-level JSON structure (cfg, io, ch, aux, bus, main, mtx, dca, mgrp, fx, cards, play, rec).
- **Values**: floats are dB (fader **−144 = off**); ints for enums; strings for names/notes. Type matters — send `f`, `i`, or `s` exactly.
- Read: `/ch/1/fdr` → reply carries `[value][scaled][internal]` triplets.
- Max UDP message **32 kB**.
- Subscriptions: one client subscribed to unsolicited updates; keepalive ~10 s.

## Workflow

1. **Discover**: `wing_osc.py sweep 172.20.10.0/28` (or whatever subnet the desk is on). Use the same network as the console.
2. **Identify**: `wing_osc.py probe <ip>` confirms model/FW.
3. **Read/write**:
   ```bash
   wing_osc.py get --host <ip> /ch/1/fdr
   wing_osc.py set --host <ip> /ch/2/fdr -2.0    # fader to −2 dB  (float)
   wing_osc.py set --host <ip> /ch/1/mute 1      # mute on          (int)
   wing_osc.py set --host <ip> /ch/1/tags "Rev"  # name/label       (string)
   wing_osc.py tree --host <ip> /bus             # list bus children
   ```
4. **Verify**: any set should be followed by a `get` read-back of the same node.

## Tool: `scripts/wing_osc.py`

Full CLI (stdlib-only raw OSC — no dependency). Run selftest after any edit:
`wingay/python wing_osc.py selftest` — it byte-compares encoder output
against known-good OSC hex (`/?` = `2f3f00002c000000`, /ch/2/fdr float =
`…2c660000c0000000`), so the wire format can never silently rot.

## Pitfalls

- **Encoder splat**: `encode_osc(addr, *args)` — passing a list as one arg
  makes the encoder raise `unsupported arg type`. Always unpack.
- **Windows WSAECONNRESET (10054)**: UDP to a dead host can surface as a
  hard ICMP port-unreachable instead of a clean timeout. Treat winerror
  10054 as "no reply", not a crash.
- **Raw paths**: passing MSYS-style `/c/...` paths to Windows python breaks
  python's `open()` (it wants `C:\...`). Use native paths.
- **Min-Max loops**: in exactly one place (`sweep`), cap per-host timeout
  (~0.4 s) so a scan of a /24 doesn't take minutes.
- Class/name drift: rename a class or fn and grep every call site (we hit
  a stale `WingClient` reference that broke three commands).

## Files

- `scripts/wing_osc.py` — the CLI (sweep/probe/get/set/tree/selftest).
- Full protocol reference: official doc lives in the skill repo; `references/`
  for workflows reused often.