#!/usr/bin/env python3
"""Smoke-test the Hermes `serve` gateway JSON-RPC/WebSocket protocol.

Usage:
    python gateway_smoke_test.py <token> [port]

Run it with the Hermes venv python (which has aiohttp):
    "<hermes-home>/hermes-agent/venv/Scripts/python.exe" gateway_smoke_test.py <token>

Verifies, against a live `hermes serve`:
  1. WS auth with ?token=
  2. session.create (returns live sid + model)
  3. prompt.submit streaming (counts message.delta events; prints final text)
  4. session.list
  5. session.history (role sequence)

A clean run proves any custom client talking to the same endpoint/token will work.
"""
import asyncio
import json
import sys

import aiohttp

TOKEN = sys.argv[1] if len(sys.argv) > 1 else ""
PORT = sys.argv[2] if len(sys.argv) > 2 else "9119"
WS = f"ws://127.0.0.1:{PORT}/api/ws?token={TOKEN}"
PROBE = "Reply with exactly the word PONG and nothing else."


async def main():
    async with aiohttp.ClientSession() as sess:
        async with sess.ws_connect(WS, timeout=30) as ws:
            # 1 + 2: create a session
            await ws.send_json({"jsonrpc": "2.0", "id": 1, "method": "session.create", "params": {}})
            sid = None
            while True:
                m = await ws.receive_json(timeout=60)
                if m.get("id") == 1:
                    r = m["result"]
                    sid = r["session_id"]
                    print(f"session.create OK  live_sid={sid}  model={r['info'].get('model')}")
                    break

            # 3: submit a probe and count deltas
            await ws.send_json({"jsonrpc": "2.0", "id": 2, "method": "prompt.submit",
                                "params": {"session_id": sid, "text": PROBE}})
            deltas = 0
            complete = {}
            while True:
                m = await ws.receive_json(timeout=300)
                if m.get("id") == 2:
                    continue
                if m.get("method") == "event":
                    ev = m["params"]
                    t = ev.get("type")
                    if t == "message.delta":
                        deltas += 1
                    elif t == "message.complete":
                        complete = ev.get("payload", {})
                        break
                    elif t == "error":
                        print("ERROR event:", ev.get("payload"))
                        sys.exit(1)
            print(f"prompt.submit OK  delta_events={deltas}  "
                  f"complete_text={complete.get('text')!r}  status={complete.get('status')}")

            # 4: list
            await ws.send_json({"jsonrpc": "2.0", "id": 3, "method": "session.list", "params": {"limit": 5}})
            while True:
                m = await ws.receive_json(timeout=30)
                if m.get("id") == 3:
                    print(f"session.list OK  sessions={len(m['result']['sessions'])}")
                    break

            # 5: history
            await ws.send_json({"jsonrpc": "2.0", "id": 4, "method": "session.history",
                                "params": {"session_id": sid}})
            while True:
                m = await ws.receive_json(timeout=30)
                if m.get("id") == 4:
                    roles = [x.get("role") for x in m["result"]["messages"]]
                    print(f"session.history OK  roles={roles}")
                    break

    print("ALL GATEWAY CHECKS PASSED")


if __name__ == "__main__":
    asyncio.run(main())
