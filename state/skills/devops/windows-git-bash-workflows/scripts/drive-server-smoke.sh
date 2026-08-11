#!/bin/bash
# drive-server-smoke.sh — foreground wrapper for smoking a local server through
# the Hermes terminal on Windows git-bash. Workaround for the host quirk where
# terminal(background=true) exits 1 with zero output when launching node.
#
# Usage (run in the server's project dir):
#   bash drive-server-smoke.sh [start_cmd] [smoke_script] [ready_sleep_secs]
# Defaults:
#   start_cmd  = "NODE_ENV=production node dist/server.cjs"
#   smoke_script = "scripts/contract-smoke.sh"
#   ready_sleep_secs = 3
#
# Customize by editing the variables below or passing positional args.

START_CMD="${1:-NODE_ENV=production node dist/server.cjs}"
SMOKE_SCRIPT="${2:-scripts/contract-smoke.sh}"
SLEEP_SECS="${3:-3}"

# Start server detached inside this shell (NOT via terminal background=true)
$START_CMD > /tmp/server-smoke.log 2>&1 &
SERVER_PID=$!

# Give it time to bind
sleep "$SLEEP_SECS"

# Health check: fail fast with the log if the port is dead
if ! curl -s -m 3 "http://127.0.0.1:3000/api/v1/health" > /dev/null 2>&1; then
    echo "SERVER DID NOT COME UP — log tail:"
    grep -v '^$' /tmp/server-smoke.log | tail -20
    kill "$SERVER_PID" 2>/dev/null
    exit 1
fi

bash "$SMOKE_SCRIPT"
RC=$?

kill "$SERVER_PID" 2>/dev/null
exit $RC