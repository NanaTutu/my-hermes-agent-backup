#!/usr/bin/env bash
# =============================================================================
# hermes_sync.sh — deploy the mirrored Hermes config snapshot from a repo clone
# into a live Hermes home.  Runs on the CONSUMER (Linux) box.
#
# Model:  ONE writer (Windows box, Hermes Backup Bot plugin) + MANY readers.
#         The Linux box must NEVER push back to the repo — that two-writer
#         setup is what previously diverged this repo and rejected pushes.
#
# The repo's state/ holds two kinds of files:
#   * portable (authored, worth copying) : skills, SOUL.md, memories, cron
#   * machine-local (must not copy)      : config.yaml, channel_directory.json,
#                                          gateway_state.json, cache yaml/json
#
# This script copies ONLY the portable trees into HERMES_HOME.  config.yaml and
# the runtime JSONs are left alone so the Linux box keeps its own API model
# paths, gateway identity, and caches.  One writer, many readers, no conflicts.
#
# The copy is additive -- existing files are refreshed from the snapshot, but
# nothing in HERMES_HOME is ever deleted -- so a skill that only exists locally
# survives untouched.
#
# Usage:
#   ./hermes_sync.sh                      # run inside the repo clone
#   HERMES_HOME=/home/tutu/.hermes ./hermes_sync.sh
#
# Exit: 0 done / up-to-date, 1 error, 2 no portable snapshot present.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${HERMES_SYNC_REPO_ROOT:-$SCRIPT_DIR}"
SNAPSHOT_DIR="$REPO_ROOT/state"
LIVE_HOME="${HERMES_HOME:-$HOME/.hermes}"
LIVE_HOME="${LIVE_HOME%/}"

log() { printf '[hermes-sync] %s\n' "$*"; }
die() { log "ERROR: $*"; exit 1; }

log "snapshot : $SNAPSHOT_DIR"
log "live home: $LIVE_HOME"

[[ -d "$SNAPSHOT_DIR" ]] || die "no $SNAPSHOT_DIR under $REPO_ROOT — git already cloned/pulled?"

# --------------------------------------------------------------------------
# 1) Refresh the local snapshot from the upstream (Windows) writer.
# --------------------------------------------------------------------------
if [[ -d "$REPO_ROOT/.git" ]]; then
    log "git pull (ff-only) from origin…"
    git -C "$REPO_ROOT" pull --ff-only origin \
        || die "pull failed (diverged?). Reconcile here manually, then re-run."
else
    log "warn: $REPO_ROOT is not a git clone; deploying whatever snapshot is already present."
fi

# --------------------------------------------------------------------------
# 2) Copy portable trees into the live home (merge, never delete).
# --------------------------------------------------------------------------
PORTABLE_TREES=(SOUL.md skills memories cron)

has_any=0
for entry in "${PORTABLE_TREES[@]}"; do
    [[ -e "$SNAPSHOT_DIR/$entry" ]] && has_any=1
done
(( has_any == 1 )) || die "portable snapshot empty/absent under $SNAPSHOT_DIR"

for entry in "${PORTABLE_TREES[@]}"; do
    src="$SNAPSHOT_DIR/$entry"
    [[ -e "$src" ]] || continue
    mkdir -p "$LIVE_HOME"
    if [[ -f "$src" ]]; then
        cp -f "$src" "$LIVE_HOME/$entry"
        log "  update  $entry"
    elif [[ -d "$src" ]]; then
        mkdir -p "$LIVE_HOME/$entry"
        if command -v rsync >/dev/null 2>&1; then
            # --update: never overwrite a loc-ally newer file; add new files.
            rsync -a --update "$src/" "$LIVE_HOME/$entry/"
        else
            cp -rp "$src/." "$LIVE_HOME/$entry/"
        fi
        log "  sync    $entry/ -> $LIVE_HOME/$entry/"
    fi
done

log "done. portable config deployed to $LIVE_HOME."
printf '%s\n' "NOTE: machine-local files (config.yaml, gateway_state.json," \
              "channel_directory.json, caches) were NOT touched — they stay" \
              "local to this box."
exit 0