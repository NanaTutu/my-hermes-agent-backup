# WING Snapshot (`.snap`) JSON Format — Verified

Sources: official WING OSC Remote Protocol doc (Maillot) + community TypeScript
schema (`wing-snap-types`, derived from real exports) + observed `.snap` files
(reference-by-example from the worship-audio-agent-skills repo). Where the OSC doc's
"description/scopes/ae_data/ce_data" prose conflicts with observed files, the
**observed envelope** below wins — real console exports look like this.

## Ports & Probe (OSC)

- Native remote: TCP/UDP **2222**; OSC: UDP **2223**.
- Probe: send `/?` → reply string, e.g.
  `WING,192.168.1.71,PGM,ngc-full,NO_SERIAL,1.07.2-40-g1b1b292b:develop`
- OSC types: `i` int32, `f` float32, `s` string, `b` blob. Max UDP message: **32 kB**.
- OSC parameter tree mirrors `ae_data`; control-surface state lives under `$ctl` (`ce_data`).

## The `.snap` Envelope (top level)

```json
{
  "type": "snapshot.11",          // "snapshot.xx" — REQUIRED, exact prefix
  "creator_fw": "1.07…",          // console firmware
  "creator_model": "wing-fullsize"| "wing-compact" | "wing-rack",
  "creator_version": "1.07",
  "creator_sn": "…",
  "creator_name": "…",
  "created": "YYYY-MM-DD HH:MM:SS",  // space-separated, no T/Z (observed: "2026-05-16 15:43:39")
  "active_show": "I:/…shw",
  "active_scene": "I:/…snap",      // link back to itself
  "ae_data": { … },                // audio engine — THE SHOW
  "ce_data": { "cfg","layer","user","gpio","safes","daw","midi","osc","lib" },  // surface state
  "ae_globals": { … },             // engine globals (clkrate, clksrc, startmute, usbacfg…)
  "ce_globals": { … }
}
```

**Validated against a real console export** (Wing fullsize, FW 3.1, 2026-05): the file above IS
the exact shape a real snapshot has — same root keys, same channel keys, no `scopes`/`description`
keys present. Trust this, not older community claims about "four sections".

- **Scope table** (`scopes`): described by the OSC docs as Boolean groups for
  ch 1..40 / aux 1..8 / bus 1..16 / main 1..4 / mtx 1..8 / fx 1..16 / routin 1..13 /
  routout 1..11 / cfg / area / data. **Observed `.snap` files often omit it** — the
  recall mask lives in the console UI. Treat as optional.
- `description`: documented in OSC prose, rarely present in raw files — the envelope
  metadata fields (`creator_*`, `created`) take the description role.

## `ae_data` — Audio Engine

| Key | Contents |
|---|---|
| `cfg` | globals: mainlink, dcamgrp, mon A/B (lvl/pan/peq), solo, talk, user keys |
| `io` | patch bays: `io.in.<GRP>.<n>.name`, `io.in.<GRP>.<n>.conn`; `io.out.<GRP>.<n> = {grp,in}`. Observed groups: `LCL, AUX, A, B, C, SC, USB, CRD, MOD, PLAY, AES, USR, OSC` (in) — in/out mirrors |
| `ch` | 40 input channel strips |
| `aux` | 8 aux returns |
| `bus` | 16 buses + sends |
| `main` | 4 mains (L/R/C/M) |
| `mtx` | 8 matrices |
| `dca` | DCA groups |
| `mgrp` | mute groups |
| `fx` | 16 FX/insert slots |
| `cards` | W-LIVE / W-MADI card settings |
| `play` / `rec` | USB/SD recorder (repeat, resolution, channels) |

## Channel Strip (`ae_data.ch.<n>` — the fields to edit)

```json
{ "in": { "set": {"trim":0,"inv":false,"bal":0,"dly":0,"dlyon":false},
          "conn": {"grp":"LCL","in":1,"altgrp":"OFF","altin":1} },
  "flt": { "lc":false,"lcf":20, "hc":false,"hcf":20000 },       // HPF/LPF
  "clink": false, "col": 1, "name": "Lead Vocal", "icon": 1,   // col=color idx, icon=idx
  "led": false, "mute": true, "fdr": -6.5,                     // fader = dB, -144 = off
  "pan": 0, "wid": 1.0, "solosafe": false, "mon": "A",
  "proc": "GEDI",
  "peq": {"on":false, "1g":0,"1f":250,"1q":1.0, …},            // 3-band pre-EQ
  "gate": {"on":false,"mdl":"GATE", "thr":-60,"att":1,…},
  "eq":   {"on":false,"mdl":"STD", "1g":0,"1f":250,"1q":1.0, … },  // 6-band EQ
  "dyn":  {"on":false,"mdl":"COMP", "thr":-20,"ratio":2,"att":5,…},
  "preins": {"on":false, "ins":"NONE"}, "postins": {"on":false},
  "main": {"1":{"on":true,"bal":0,"tap":"PRE"}, "2":{…}, …},   // sends to Mains 1..4
  "send": {"1":{"on":0,"lev":-144,"bal":0,"tap":"PRE"}, …},      // bus sends 1..16
}
```

Channel field semantics (verified against types + observed files):

| Field | Type | Meaning |
|---|---|---|
| `name` | string | channel label |
| `fdr` | number (dB) | fader; **−144 = effectively off**, 0 = unity |
| `mute` | bool | channel mute |
| `pan` | number | −100..100 |
| `wid` | number | stereo width |
| `col` / `icon` | int | scribble color / icon index |
| `mon` | `"A"`\|`"B"` | monitor selection |
| `in.conn.grp/in` | string/int | patch source e.g. `LCL.1`, plus `altgrp`/`altin` alternate |
| `eq` | object | 6-band EQ: `{on, mdl:"STD", "1g","1f","1q", …}` |
| `send.<n>` | object | bus send: `{on, lev (dB), bal, tap: "PRE"|"POST"|"GRP"}` |

## Editing Rules for WING

1. `fdr` is a **dB number** (−144 = effectively off; 0 = unity). NOT a 0..1 float — unlike X32 scene dB text vs X32 OSC float convention.
2. `type` MUST start with `snapshot.` — console checks it. Keep version "snapshot.11" unless a higher one is required.
3. Saves are **one long JSON string** (no newlines, no trailing newline) — that's what the console/Edit produce; use `json.dump(f, separators=(",",":"))`.
4. Don't drop unknown envelopes: preserve `ae_globals`/`ce_globals` and any unrecognized keys — console versions vary.
5. Always validate: `python wing_snap_audit.py` + open in WING-Edit before USB delivery; WING-Edit rejects malformed snapshots.
6. Shows vs snaps: a `.shw` (show) bundles many `.snap`s (scene list) and `.snip`s (snippets) — editing a scene = editing the snap JSON; the show's directory structure is just a text JSON manifest.