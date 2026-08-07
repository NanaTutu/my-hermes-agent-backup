---
name: behringer-mixer-scenes
description: "Use when authoring Behringer X32/X-Air/WING scene files."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [behringer, x32, x-air, wing, osc, scenes, snapshots, audio]
    related_skills: [obsidian, songsee]
---

# Behringer Mixer Scene & Snapshot Authoring

## Overview

Create, edit, validate, and deploy **scene files** (`.scn`), **snippet files** (`.snp`), and **snapshot files** (WING JSON) for Behringer digital mixers: the **X32/M32** family, **X-Air (XR12/16/18)**, and the **WING**. All three share one DNA: their scene files are *text files of OSC node lines* (X32/X-Air) or *JSON* (WING) encoding the console's parameter tree. Own the OSC address map and you can author presets offline and load them via USB or OSC — no console needed until the final verification step.

## When to Use

- User asks to create/prepare a scene, snippet, snapshot, showfile, or preset for a Behringer console.
- User needs to reconfigure channels/buses/EQ/FX for an event and wants a file the mixer can load.
- Building church-service scenes (e.g. "Worship", "Sermon", "After-service") from a spec.
- Scripting mixer state: generate many scenes programmatically, then load them via OSC or USB.

**Don't use for**: live fader-twiddling in real time (that's OSC automation, not file authoring; the same address map applies).

## Console / Format Quick Reference

| Console | Scene ext | File format | OSC port | Offline editor |
|---|---|---|---|---|
| X32 / M32 family | `.scn` scenes, `.snp` snippets | Text: OSC node lines | **10023** UDP | X32-Edit |
| X-Air XR12/16/18 | `.scn` | Text: OSC node lines | **10024** UDP | X-Air Editor |
| WING | `.snap` / `.snip` / `.chn` | JSON envelope: `type` + `ae_data` + `ce_data` + globals | UDP 2223 (native 2222) | WING-Edit |

Primary protocol references (already downloaded + extracted):
- `C:\Users\bohen\AppData\Local\Temp\x32_osc.txt` — Unofficial X32/M32 OSC Remote Protocol (Patrick-Gilles Maillot; the authoritative OSC/scene-format reference).
- `C:\Users\bohen\AppData\Local\Temp\wing_osc.txt` — WING OSC documentation (same author).
- `wing_osc.pdf` / `x32_osc.pdf` originals in the same folder.

## The X32/M32 Scene File Format (`.scn`)

Plain text; one OSC *node command* per line, in a fixed order — exactly what the console writes when you export a scene and reads when you load one.

### Header line

```
#4.0# "Scene name" "Scene note" %000000000 1    <- scene file
#2.7# "Snippet name" 31473663 1 66305 449 1     <- snippet file
```

- `#4.0#` is the file version (older console exports may write `#3.x#`; the reader is backwards-compatible).
- `%000000000` = 8 scene-safety bits (one per safety category) + a trailing 0; the file ends the header with `1`.
- Snippet header's 4 numbers = eventtyp / channels / auxbuses / maingrps filter masks saved in the snippet.

### Line format

`/address value1 value2 ...` — same visual as OSC but **without type tags**; values in console UI form (`"Name"`, `ON`/`OFF`, `+4.5`, `-oo`, `%00000001`). Lines starting with `#` are comments.

Real lines copied from a real scene (`scripts/hope2022-sample.scn`) — use these as patterns; each node group has a *fixed* argument order:

```text
/ch/01/config "Solly" 41 WH 32         ; name, icon, color, source (4 args, verified)
/ch/01/preamp +4.5 OFF ON 24 73        ; trim dB, phantom, HPF on/off, ... (see reference)
/ch/01/gate ON GATE -67.5 60.0 1 502 983 0
/ch/01/dyn ON COMP PEAK LOG -45.5 2.5 3 2.50 10 5.64 20 PRE 0 100 OFF
/ch/01/eq ON
/ch/01/mix OFF +3.0 ON +0 OFF -oo     ; mute, fader, L/R, pan, mute, fader (-oo = -inf)
/ch/01/grp %00000001 %000011
/bus/01/config "Monitor A" 64 YE
/bus/01/mix OFF -6.9 OFF +0 OFF -oo
/bus/09/mix ...                       ; FX sends live on buses 9-16 on X32
/main/st/mix ON -17.4 +0
/dca/1 ON +3.5
/fx/1/source MIX13 MIX13
/main/st/config "MAINS" 66 WH
```

### Node groups in a full scene (~2100 lines)

| Group | Covers |
|---|---|
| `/config/*` | chlink, auxlink, fxlink, buslink, mtxlink, mute, mono, solo, talk, osc, routing, userrout, userctrl, tape, amixenable, dp48 |
| `/ch/01..32` | full channel: config (name/icon/color/source), delay, preamp (trim/phantom/HPF), gate+filter, dyn+filter, insert, 4-band EQ + per-band, mix (mute/fader/pan/16 sends), grp (DCA/mute groups), automix |
| `/auxin/01..08` | stereo aux returns: config, preamp, EQ, mix, grp |
| `/fxrtn/01..08` | FX returns: config, EQ, mix |
| `/bus/01..16` | bus strips: config, dyn+filter, insert, 6-band EQ, mix |
| `/mtx/01..06` | matrix sends |
| `/main/st`, `/main/m` | stereo and mono mains: config, dyn, insert, EQ, mix |
| `/dca/1..8` | DCA group faders |
| `/fx/1..8` | FX engines: source + 31 parameters |
| `/outputs/main, aux, p16, aes, rec` | output tap points |
| `/headamp/000..127` | stage-box/split preamps |

## X-Air (XR12/16/18) Scenes

Same OSC-node text format; header version may differ (the XR18 app exports `#2.1# "name"` internally). Port: **UDP 10024**. XR18 = 16 input channels + 2 AUX in / USB, no DCA — verify per model before generating files that reference DCA.

## WING Snapshot/JSON Format

WING show files are **JSON envelopes** (tested against real-exports-derived schema — the OSC
doc's "four sections" prose describes snapshot *metatr*, not the file):

```json
{"type": "snapshot.11", "creator_fw": "...", "creator_model": "wing-fullsize",
 "created": "...", "active_show": "...", "active_scene": "...",
 "ae_data": {"cfg": {...}, "io": {...}, "ch": {...}, "bus": {...}, "main": {...},
             "mtx": {...}, "fx": {...}, ...},
 "ce_data": {"user": {...}},
 "ae_globals": {...}, "ce_globals": {...}}
```

- A saved WING snapshot is **one long JSON string** (no newlines) on disk — parse with `json.load`.
- `type` MUST start with `snapshot.` (console rejects otherwise). `scopes`/`description` from the
  OSC doc are optional in real files; channel strips are `ae_data.ch.<n>` with `name`, `fdr` (dB,
  −144 = off), `mute`, `pan`, `eq`, `send`.
- `ae_data` = audio-engine values (the show); `ce_data` = control-surface/UI state (OSC `$ctl`);
  `x_globals` = global settings (clock, format).
- OSC probe: send `/?`; reply returns model/FW. Max UDP message 32 kB.
- **Full field map: `references/wing-json-format.md`; validator: `scripts/wing_snap_audit.py`.**

## Creating a Scene File — the Workflow

1. **Start from a real base.** If a real scene exists (console USB export, X32-Edit export, or `scripts/hope2022-sample.scn`), copy and patch it. That preserves valid structure and all boilerplate.
2. **Write the target-state spec** — per channel: name/icon/color/source, preamp trim dB, HPF, gate/dyn/EQ on, fader dB, pan, bus sends, FX types. Present as a markdown table to the user before generating.
3. **Generate** the `.scn` by patching the copy (add/alter `/ch/NN` lines; with `scripts/scn_audit.py` verify).
4. **Validate offline first**: re-run the audit (`scn_audit.py` for X32/X-Air text; `wing_snap_audit.py` for WING), then open in the free editor — **X32-Edit** / **WING-Edit** reject malformed files.
5. **Deliver**: FAT32 USB → console **Setup → Scene Load**; WING via WING-Edit show/hub; or push live over OSC.

## Deployment via OSC (no USB)

Ports: X32/M32 **10023**, X-Air **10024**, WING **2223**. Watch the **value representation** (see pitfalls #4).

```python
from pythonosc.udp_client import SimpleUDPClient
c = SimpleUDPClient("192.168.1.100", 10023)
c.send_message("/ch/01/config/name", "Acoustic")
c.send_message("/ch/01/preamp/trim", 12.5)     # dB float
c.send_message("/ch/01/mix/fader", 0.75)          # linear: 0dB ≈ 0.75, +10 ≈ 1.0
c.send_message("/ch/01/mix/pan", -45)             # -100..100
c.send_message("/load", ["scene", 1, "SceneName"])  # scene recall
```

## Common Pitfalls

1. **Format-family confusion**: X32/X-Air scenes = text OSC lines; WING = JSON. Never drop X32 lines into a `.snap` or vice versa.
2. **Headers**: keep the version from a working export; `#4.0#` is broadly readable, but don't invent newer header numbers.
3. **`#` comments**: any line starting with `#` is a comment — the header must be the only `#` line unless you intend comments. Never embed `#` inside a string value.
4. **dB text vs linear float**: scene files carry UI dB text (`-12.5`, `-oo`); live OSC `/mix/fader` takes a *linear* 0..1 (0 dB ≈ 0.75, 1.0 ≈ +10, -60 ≈ 0). Sending a dB string to an OSC fader is a classic bug.
5. **Scene-safes bits** (`%000000000`): respect existing values when editing real files; safes gate which categories load.
6. **Big blobs**: WING snapshots exceed 25 KB — read/write as files, never inline.
7. **Foreign state**: sample scenes from another console carry device-specific state (headamp numbering, FX slot types) — preview before production use.

## Verification Checklist

- [ ] Scene file parses in X32-Edit / WING-Edit without errors; header line exact.
- [ ] Node addresses match the verified list in `references/x32-osc-format.md`.
- [ ] Every `/ch/NN` block: `config` line (name/icon/color/source) present; fader in `/ch/NN/mix` present.
- [ ] Levels correct representation (scene = dB text; OSC set = linear float).
- [ ] WING: file is valid JSON; `type` starts with `snapshot.`; `ae_data` with `cfg`/`io`/`ch`; optional `ce_data`/globals (use `scripts/wing_snap_audit.py`).
- [ ] Sample scene opens on the real console (or in the editor) before production use.

## References & Scripts

- `references/x32-osc-format.md` — verified node groups, header formats, snippet masks, ports (from `x32_osc.txt`).
- `references/wing-json-format.md` — WING snapshot/JSON layout + OSC notes (from `wing_osc.txt`).
- `scripts/hope2022-sample.scn` — real scene file to copy/patch.
- `scripts/scn_audit.py` — validate & summarize a `.scn` (header, nodes, bus map) before delivery.