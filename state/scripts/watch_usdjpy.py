#!/usr/bin/env python
"""Exness live-position watcher for USD/JPY ticket 23989608.

Reads the Exness web terminal via cua-driver CLI. Prints NOTHING while the
position is still open (silent watchdog). Prints a human-readable alert only
when the ticket leaves the Open tab, so the cron delivers a message exactly
when there's news worth a notification.

Usage: python watch_usdjpy.py
"""
import json
import re
import subprocess
import sys
import time

TICKET = "23989608"
ENTRY = 158.367
SL = 158.620
TP = 157.600
DRIVER = "cua-driver"
TITLE = re.compile(r"USD/JPY Bid", re.IGNORECASE)
MISS_FILE = r"C:\Users\bohen\AppData\Local\Temp\usdjpy_watch_misses.txt"
MISS_LIMIT = 3  # consecutive sight-losses before we alert (transient blips stay silent)


def drv(*args, timeout=90):
    try:
        p = subprocess.run([DRIVER, *args], capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout
    except Exception as exc:  # noqa: BLE001 - do not crash the cron tick
        return -1, str(exc)


def to_json(s):
    try:
        return json.loads(s)
    except Exception:
        return None


def find_terminal():
    """Start a fresh session, list windows, return (pid, window_id) for the
    USD/JPY trading window, or (None, None) if not found."""
    drv("call", "start_session", json.dumps({"session": f"usdjpy-watch-{int(time.time())}"}))
    rc, out = drv("call", "list_windows")
    data = to_json(out)
    if not data:
        return None, None
    for w in data.get("windows", []):
        title = w.get("title") or ""
        if TITLE.search(title):
            return w.get("pid"), w.get("window_id")
    return None, None


def get_tree(pid, win):
    """Return tree_markdown of the terminal state."""
    rc, out = drv("call", "get_window_state", json.dumps({"pid": pid, "window_id": win}))
    data = to_json(out)
    if not data:
        return ""
    return data.get("tree_markdown") or ""


def position_state(tree, ticket=TICKET):
    """Return 'open', 'closed', or 'unknown'.

    Robust signal: the position is OPEN while its ticket appears in the tree
    AND the Open tab reports a positive count ('TabItem "Open N"' with N>0).
    We must NOT toggle state on the presence of the 'Closed'/'Pending' tab
    LABELS in the tab bar -- those are always present regardless of the
    selected tab, so naive label-ordering caused a false 'closed' reading.
    """
    lines = tree.splitlines()

    # Open tab count: 'TabItem "Open 2"' -> 2
    open_count = 0
    for line in lines:
        m = re.search(r'TabItem "Open (\d+)"', line)
        if m:
            open_count = int(m.group(1))

    ticket_in_tree = ticket in tree
    if ticket_in_tree and open_count > 0:
        return "open"
    return "unknown"


def miss_counter(reset=False):
    """Track consecutive sight-losses in a temp file. Returns current count."""
    def _read():
        try:
            with open(MISS_FILE) as fh:
                return int(fh.read().strip() or "0")
        except Exception:
            return 0

    if reset:
        try:
            with open(MISS_FILE, "w") as fh:
                fh.write("0")
        except Exception:
            pass
        return 0
    count = _read() + 1
    try:
        with open(MISS_FILE, "w") as fh:
            fh.write(str(count))
    except Exception:
        pass
    return count


def main():
    pid, wid = find_terminal()
    if pid is None or wid is None:
        # Can't reach the terminal. Stay silent for a few consecutive blips,
        # then alert if we've genuinely lost sight -- never invent an outcome.
        misses = miss_counter()
        if misses >= MISS_LIMIT:
            print(
                f"USD/JPY position #{TICKET} watcher: cannot locate the Exness "
                "trading terminal for several consecutive checks. The position "
                f"(entry {ENTRY}, SL {SL}, TP {TP}) may have closed or the "
                "terminal may have been closed. Please confirm manually."
            )
        return 0

    miss_counter(reset=True)
    tree = get_tree(pid, wid)
    if not tree:
        return 0  # transient capture failure; stay quiet this tick

    if position_state(tree) == "open":
        return 0  # still open -> no news, deliver nothing

    # Ticket left the Open table. Emit a message prompting manual confirmation
    # (never guess TP-hit vs SL-hit here -- the Open/Closed semantics require
    # a Closed-tab read we don't force in a silent watcher).
    print(
        f"USD/JPY position #{TICKET} is no longer in the Open tab "
        f"(entry {ENTRY}, SL {SL}, TP {TP}). "
        "It has likely closed on TP or SL — please confirm the outcome in the "
        "Exness terminal (Closed tab) for the realized P/L."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())