#!/usr/bin/env python3
"""
wing_osc.py — drive a Behringer WING console over OSC (UDP 2223).

Raw-OSC implementation (stdlib only; no python-osc dependency needed).

Usage:
    wing_osc.py sweep [cidr]                       # scan subnet for WING consoles
    wing_osc.py probe <ip>                       # identify a console: send /?
    wing_osc.py get --host HOST /ch/1/fdr        # read a node
    wing_osc.py set --host HOST /ch/2/fdr -2.0   # float (fader -2 dB)
    wing_osc.py set --host HOST /ch/1/mute 1     # int (mute on)
    wing_osc.py set --host HOST /ch/1/tags "Rev" # string
    wing_osc.py tree --host HOST /               # list children of a node
    wing_osc.py selftest                         # verify OSC byte encoding
"""

import argparse
import ipaddress
import socket
import struct
import sys
from typing import List, Optional, Tuple, Union

OSC_PORT = 2223
MAX_MSG = 32 * 1024  # documented WING max UDP message size


def _pad4(data: bytes) -> bytes:
    return data + b"\x00" * ((4 - len(data) % 4) % 4)


def encode_osc(address: str, *args: Union[float, int, str]) -> bytes:
    """Encode an OSC message (address + type tags + args, 4-byte aligned)."""
    out = bytearray(_pad4(address.encode("ascii")))
    tags = ""
    payload = b""
    for a in args:
        if isinstance(a, bool):
            a = 1 if a else 0
        if isinstance(a, int):
            tags += "i"
            payload += struct.pack(">i", a)
        elif isinstance(a, float):
            tags += "f"
            payload += struct.pack(">f", a)
        elif isinstance(a, str):
            tags += "s"
            payload += _pad4(a.encode("utf-8"))
        else:
            raise ValueError(f"unsupported arg type {type(a)}")
    out += _pad4(("," + tags).encode("ascii"))
    out += payload
    return bytes(out)


def decode_osc(data: bytes) -> Tuple[str, List]:
    """Decode an OSC message into (address, [args]). WING replies use f/i/s."""

    def take(raw: bytes, offset: int) -> Tuple[str, int]:
        end = raw.index(b"\x00", offset)
        return raw[offset:end].decode("utf-8", "replace"), (end // 4 + 1) * 4

    addr, off = take(data, 0)
    tags_str, off = take(data, off)
    tags = tags_str.lstrip(",")
    args: List = []
    for t in tags:
        if t == "s":
            s, off = take(data, off)
            args.append(s)
        elif t == "i":
            args.append(struct.unpack_from(">i", data, off)[0])
            off += 4
        elif t == "f":
            args.append(struct.unpack_from(">f", data, off)[0])
            off += 4
        elif t == "b":
            ln = struct.unpack_from(">i", data, off)[0]
            off += 4
            args.append(data[off:off + ln])
            off += (ln + 3) // 4 * 4
        else:  # unknown tag — skip what we can't know
            args.append(None)
            off += 4
    return addr, args


class WingOSC:
    def __init__(self, host: str, port: int = OSC_PORT, timeout: float = 2.0):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(timeout)

    def send(self, address: str, args=()) -> Optional[Tuple[str, List]]:
        try:
            # NOTE: must splat — passing args as one tuple raises
            # "unsupported arg type <class 'tuple'>"
            self.sock.sendto(encode_osc(address, *args), (self.host, self.port))
            data, _ = self.sock.recvfrom(65535)
        except socket.timeout:
            return None
        except OSError as e:
            # Windows: UDP to a dead host raises WSAECONNRESET (10054) via
            # ICMP port-unreachable — treat as no-reply, not a crash.
            if e.winerror == 10054:
                return None
            raise SystemExit(f"network error reaching {self.host}:{self.port}: {e}")
        return decode_osc(data)


def _fmt(args: List) -> str:
    return "  |  ".join(
        "s:" + a if isinstance(a, str) else
        ("i:" + str(a) if isinstance(a, int) else f"f:{a:.6g}")
        for a in args
    )


def cmd_probe(host: str) -> None:
    c = WingOSC(host)
    reply = c.send("/?")
    if reply is None:
        print(f"no reply from {host}:{OSC_PORT} (is remote control on? right IP?)")
        sys.exit(1)
    addr, args = reply
    print(f"probe -> {addr}:")
    for a in args:
        print(f"   {a}")


def cmd_sweep(cidr: str) -> None:
    net = ipaddress.ip_network(cidr, strict=False)
    found = 0
    print(f"sweeping {net} for WING consoles (UDP {OSC_PORT})...")
    for ip in net.hosts():
        c = WingOSC(str(ip), timeout=0.4)
        try:
            reply = c.send("/?")
            if reply:
                print(f"  FOUND {ip}: {reply[1]}")
                found += 1
        except SystemExit:
            continue
    print(f"done — {found} console(s) found")


def cmd_get(cfg) -> None:
    c = WingOSC(cfg.host)
    reply = c.send(cfg.node)
    if reply is None:
        print("no reply — node may not exist or console busy")
        sys.exit(1)
    addr, args = reply
    print(f"{addr}\n {_fmt(args)}")


def cmd_set(cfg) -> None:
    c = WingOSC(cfg.host)
    raw = " ".join(cfg.args) if isinstance(cfg.args, list) else cfg.args
    # WING accepts typed args: ints as i, floats as f, strings as s
    if raw is None or raw == "":
        print("no value given for set")
        sys.exit(1)
    try:
        arg = int(raw)
    except ValueError:
        try:
            arg = float(raw)
        except ValueError:
            arg = raw  # string — keep as-is
    reply = c.send(cfg.node, [arg])
    if reply is None:
        print("no reply — console may be offline or value rejected")
        sys.exit(1)
    addr, args = reply
    if isinstance(arg, int):
        kind = "int"
    elif isinstance(arg, float):
        kind = "float"
    else:
        kind = "string"
    print(f"set {cfg.node} ({kind} {arg!r})")
    print(f"  <- {addr}: {_fmt(args)}")


def cmd_tree(cfg) -> None:
    c = WingOSC(cfg.host)
    reply = c.send(cfg.node)
    if reply is None:
        print(f"no reply for {cfg.node}")
        sys.exit(1)
    addr, args = reply
    print(f"children of {addr}:")
    for a in args:
        if isinstance(a, str):
            print(f"  {a}")


def cmd_selftest() -> None:
    expected = [
        (encode_osc("/?"), b"/?\x00\x00,\x00\x00\x00"),
        (encode_osc("/ch/2/fdr", -2.0),
         b"/ch/2/fdr\x00\x00\x00,f\x00\x00" + struct.pack(">f", -2.0)),
    ]
    for got, want in expected:
        print(f"[{'OK' if got == want else 'MISMATCH'}] {got.hex()}")
    addr, args = decode_osc(encode_osc("/ch/1/mute", 1))
    ok = addr == "/ch/1/mute" and args == [1]
    print(f"[{'OK' if ok else 'MISMATCH'}] round-trip: {addr} args={args}")


def main() -> int:
    p = argparse.ArgumentParser(description="WING OSC remote control")
    sub = p.add_subparsers(dest="cmd", required=True)

    pp = sub.add_parser("probe")
    pp.add_argument("host")

    sw = sub.add_parser("sweep")
    sw.add_argument("cidr", nargs="?", default="192.168.1.0/24")

    g = sub.add_parser("get")
    g.add_argument("--host", default="192.168.1.200")
    g.add_argument("node")

    s = sub.add_parser("set")
    s.add_argument("--host", default="192.168.1.200")
    s.add_argument("node")
    s.add_argument("args", nargs="+")

    t = sub.add_parser("tree")
    t.add_argument("--host", default="192.168.1.200")
    t.add_argument("node", default="/", nargs="?")

    sub.add_parser("selftest")

    a = p.parse_args()
    if a.cmd == "probe":
        cmd_probe(a.host)
    elif a.cmd == "sweep":
        cmd_sweep(a.cidr)
    elif a.cmd == "get":
        cmd_get(a)
    elif a.cmd == "set":
        cmd_set(a)
    elif a.cmd == "tree":
        cmd_tree(a)
    elif a.cmd == "selftest":
        cmd_selftest()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())