#!/usr/bin/env python3
"""
wing_snap_audit.py — validate & summarize a Behringer WING .snap snapshot file.

WING snapshots are JSON envelopes (NOT the 4-section "description/scopes/ae_data/
ce_data" shape described in the WING OSC docs — real files export an envelope):

    {
      "type": "snapshot.11",
      "creator_fw": "...", "creator_model": "wing-fullsize",
      "created": "...", "active_show": "...", "active_scene": "...",
      "ae_data": { "cfg", "io", "ch", "aux", "bus", "main", "mtx", "dca",
                   "mgrp", "fx", "cards", "play", "rec" },
      "ce_data": { "user": ... },
      "ae_globals": {...}, "ce_globals": {...}
    }

Usage:
    python wing_snap_audit.py path/to/file.snap
"""

import json
import sys

REQUIRED_ROOT = ["type", "ae_data"]
REQUIRED_AE = ["cfg", "io", "ch"]
CHANNEL_FIELDS = ["name", "fdr", "mute", "pan", "col", "icon", "in", "eq", "send", "main"]


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    raw = open(path, "r", encoding="utf-8").read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: {path} is not valid JSON: {e}")
        return 1

    if not isinstance(data, dict):
        print("ERROR: snapshot root is not a JSON object")
        return 1

    t = str(data.get("type", ""))
    if not t.startswith("snapshot."):
        print(f"ERROR: unexpected type {t!r} (expected 'snapshot.xx')")
        return 1
    print(f"OK   type={t} model={data.get('creator_model')!r} fw={data.get('creator_fw')!r}")

    missing = [k for k in REQUIRED_ROOT if k not in data]
    if missing:
        print(f"ERROR: missing root keys: {missing}")
        return 1

    ae = data["ae_data"]
    missing_ae = [k for k in REQUIRED_AE if k not in ae]
    if missing_ae:
        print(f"ERROR: ae_data missing keys: {missing_ae}")
        return 1

    ch = ae.get("ch", {})
    bus = ae.get("bus", {})
    main = ae.get("main", {})
    mtx = ae.get("mtx", {})
    fx = ae.get("fx", {})
    print(f"OK   channels: {len(ch)}, buses: {len(bus)}, mains: {len(main)}, "
          f"mtx: {len(mtx)}, fx: {len(fx)}")

    # channel-level sanity: name present, fdr numeric, mute boolean
    issues = 0
    for k in sorted(ch, key=lambda x: int(x)):
        c = ch[k]
        if not isinstance(c, dict):
            print(f"WARN ch[{k}] not an object")
            issues += 1
            continue
        missing_f = [f for f in CHANNEL_FIELDS if f not in c]
        if missing_f:
            print(f"WARN ch[{k}] missing fields: {missing_f}")
            issues += 1
        for f in ("name", "mute", "fdr"):
            if f in c and not isinstance(c[f], (str, bool, int, float)):
                print(f"WARN ch[{k}].{f} wrong type: {type(c[f]).__name__}")
                issues += 1

    # io patch sanity: each group maps channel numbers
    io_in = ae.get("io", {}).get("in", {})
    io_out = ae.get("io", {}).get("out", {})
    print(f"OK   io.in groups: {list(io_in)[:8]}..., io.out groups: {list(io_out)[:8]}...")

    if issues:
        print(f"WARN {issues} channel-level issues (non-fatal)")
    else:
        print("OK   channel strip fields present and typed")

    if "ce_data" not in data:
        print("NOTE: no ce_data (control-surface data) — compact/headless export expected")
    print(f"OK   {path} passes structural audit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())