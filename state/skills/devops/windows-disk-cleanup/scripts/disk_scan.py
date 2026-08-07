#!/usr/bin/env python3
"""Map disk usage fast on Windows, where `du -d1` times out.

Usage: python disk_scan.py [root]      (default C:/Users/<user>)
Prints per-child sizes in GB and breaks out AppData/Local children separately.
Uses os.scandir (much faster than MSYS du) with a wall-clock budget and
skips .git / node_modules when present.
"""
import os
import sys
import time
from collections import Counter

SKIP = {".git", "node_modules"}

def dirsize(path, t0, budget):
    total = 0
    try:
        with os.scandir(path) as it:
            for e in it:
                if time.time() - t0 > budget:
                    raise TimeoutError("budget")
                try:
                    if e.is_symlink():
                        continue
                    if e.is_dir(follow_symlinks=False):
                        if e.name in SKIP:
                            continue
                        total += dirsize(e.path, t0, budget)
                    else:
                        try:
                            total += e.stat(follow_symlinks=False).st_size
                        except OSError:
                            pass
                except PermissionError:
                    pass
    except (PermissionError, OSError):
        pass
    except TimeoutError:
        return total  # partial, marked by caller
    return total

def fmt(n, partial=False):
    g = n / 1e9
    return f"{f'{g:.2f}G' if g >= 1 else f'{n/1e6:.1f}M'}{' (partial)' if partial else ''}"

def scan(root, label, t0, budget):
    t = time.time()
    try:
        sz = dirsize(root, t0, budget)
        print(f"{fmt(sz):23s} {label}  ({time.time()-t:.0f}s)", flush=True)
    except Exception as ex:
        print(f"   ERR {label}: {ex}", flush=True)

def main():
    HOME = os.path.expanduser("~")
    root = sys.argv[1] if len(sys.argv) > 1 else HOME
    budget = float(sys.argv[2]) if len(sys.argv) > 2 else 150.0
    t0 = time.time()

    print(f"=== scanning {root} (budget {budget:.0f}s) ===", flush=True)
    for name in sorted(os.listdir(root)):
        p = os.path.join(root, name)
        if os.path.isdir(p) and not os.path.islink(p):
            scan(name, p, t0, budget)

    local = os.path.join(root, "AppData", "Local")
    if os.path.isdir(local):
        print("=== AppData/Local children ===", flush=True)
        for name in sorted(os.listdir(local)):
            p = os.path.join(local, name)
            if os.path.isdir(p) and not os.path.islink(p):
                scan("Local/" + name, p, t0, budget)

if __name__ == "__main__":
    main()