#!/usr/bin/env python3
"""List individual big files under one or more roots, sorted by size.

Usage: python find_large.py [root...] [--budget <sec>]
Defaults: roots Desktop Downloads Documents Music OneDrive; min 100MB; 80s budget.
Useful to surface the actual large files behind a bulky folder so a cleanup
decision is evidence-based.
"""
import os
import sys
import time

DEFAULT_ROOTS = ["Desktop", "Downloads", "Documents", "Music", "OneDrive"]
BUDGET = 80.0
MIN_BYTES = 100 * 1024 * 1024
SKIP = {".git", "node_modules"}

def walk(top, t0, found):
    if time.time() - t0 > BUDGET:
        return
    try:
        with os.scandir(top) as it:
            for e in it:
                if time.time() - t0 > BUDGET:
                    return
                try:
                    if e.is_symlink():
                        continue
                    if e.is_dir(follow_symlinks=False):
                        if e.name not in SKIP:
                            walk(e.path, t0, found)
                    else:
                        try:
                            s = e.stat(follow_symlinks=False).st_size
                            if s > MIN_BYTES:
                                found.append((s, e.path))
                        except OSError:
                            pass
                except (PermissionError, OSError):
                    continue
    except (PermissionError, OSError):
        pass

def main():
    home = os.path.expanduser("~")
    args = sys.argv[1:]
    budget_idx = args.index("--budget") if "--budget" in args else -1
    global BUDGET
    if budget_idx >= 0:
        BUDGET = float(args[budget_idx + 1])

    extra = [a for a in args
             if a != "--budget"
             and (budget_idx < 0 or a != args[budget_idx + 1])
             and os.path.exists(a)]
    roots = extra if extra else [os.path.join(home, d) for d in DEFAULT_ROOTS]

    t0 = time.time()
    found = []
    for r in roots:
        if os.path.isdir(r):
            before = len(found)
            walk(r, t0, found)
            joined = found[before:]
            tot = sum(s for s, _ in joined)
            print(f"{os.path.basename(r)}: {len(joined)} file(s)>100MB, ~{tot/1e9:.2f}GB", flush=True)

    print("\n=== largest files (>=100MB) ===")
    for s, p in sorted(found, reverse=True)[:40]:
        print(f"{s/1e9:6.2f} GB  {p}")

if __name__ == "__main__":
    main()