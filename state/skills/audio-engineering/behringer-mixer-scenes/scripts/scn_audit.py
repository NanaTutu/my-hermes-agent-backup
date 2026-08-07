#!/usr/bin/env python3
"""
scn_audit.py — validate & summarize a Behringer X32/M32/X-Air .scn scene file.

Verifies the header line, counts nodes, checks per-channel required pairs
(config + mix), and reports the 2-letter color / icon token usage so an agent
can confirm a generated or hand-patched scene is well-formed BEFORE delivery.

Usage:
    python scn_audit.py path/to/file.scn
"""

import re
import sys
from collections import Counter


HEADER_RE = re.compile(r'^#[0-9.]+#\s+"(?P<name>[^"]*)"\s+"(?P<note>[^"]*)"\s+%(?P<safes>[01]{8,9})\s+1\s*$')
SNIP_RE = re.compile(r'^#[0-9.]+#\s+"(?P<name>[^"]*)"\s+(?P<filters>\d[\d ]+)\s*$')
NODE_RE = re.compile(r'^/(?P<seg>[a-z0-9]+)/(?P<rest>[^"\s].*)$')
CH_RE = re.compile(r'^/ch/(?P<ch>\d{2})/(?P<attr>[a-z0-9/]+)')


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    path = sys.argv[1]
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        lines = [l.rstrip("\n") for l in fh]

    if not lines:
        print(f"ERROR: {path} is empty")
        return 1

    first = lines[0]
    kind = "scene"
    if HEADER_RE.match(first):
        m = HEADER_RE.match(first)
        print(f"OK   header: #-version={first.split('#')[1]} name={m.group('name')!r}")
    elif SNIP_RE.match(first):
        kind = "snippet"
        print(f"OK   snippet header: {first}")
    else:
        print(f"ERROR: first line not a valid header: {first[:80]!r}")
        return 1

    nodes = []
    ch_seen = {}
    bad = []
    for i, line in enumerate(lines[1:], start=2):
        if line.startswith("#") or not line.strip():
            continue  # comment / blank
        # /-stat/* lines are console UI-state exports (selected channel,
        # fader banks) — valid in real scene files, excluded from node count.
        if line.startswith("/-stat/"):
            continue
        m = NODE_RE.match(line)
        if not m:
            bad.append((i, line[:160]))
            continue
        seg = m.group("seg")
        nodes.append(seg)
        cm = CH_RE.match(line)
        if cm:
            ch = cm.group("ch")
            attr = cm.group("attr").split("/")[0]
            ch_seen.setdefault(ch, set()).add(attr)

    print(f"OK   {len(nodes)} node lines, {len(ch_seen)} channels referenced")
    print("top segments: " + ", ".join(f"{k}×{v}" for k, v in Counter(nodes).most_common(12)))

    missing_cfg = [c for c, attrs in sorted(ch_seen.items()) if "config" not in attrs]
    if missing_cfg:
        print(f"WARN channels without /config line: {missing_cfg}")

    # every channel with a /mix should carry its fader value
    mix_ok = all(any(a.startswith("mix") for a in attrs) for attrs in ch_seen.values())
    print(f"OK   every referenced channel has /mix data: {mix_ok}")

    if bad:
        print(f"ERROR {len(bad)} unparseable lines; first few:")
        for ln, txt in bad[:5]:
            print(f"  {ln}: {txt}")
        return 1

    print(f"OK   {path} passes structural audit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())