#!/usr/bin/env bash
# =============================================================================
# hermes_sync.sh — THE single entry point for deploying a Hermes state repo on
# any box. Auto-detects the OS, decides the box's ROLE, and does the right
# thing — so a fresh clone "just knows what to do" wherever it lands.
#
# ROLES
#   AUTHOR   = Windows box. Owns SOUL.md/skills/memories; the ONLY writer.
#              Delegates to hermes_backup.py (scripts/) -> PUSH to GitHub.
#   CONSUMER = any non-Windows box (Linux/macOS/BSD). Must NEVER push back —
#              a two-writer setup is what diverges the repo & rejects pushes.
#              It pulls (ff-only) and deploys the snapshot locally.
#
# OS -> role      Windows -> AUTHOR ; Linux/macOS/BSD -> CONSUMER
# This is a heuristic, not a law: override with HERMES_ROLE=author|consumer.
#
# The repo's state/ holds two kinds of files:
#   * portable (copy)    : SOUL.md, skills/, memories/, cron/
#   * machine-local (no) : config.yaml, gateway_state.json,
#                          channel_directory.json, context/provider caches
# Consumers copy ONLY the portable trees; machine-local files stay per-box.
# The copy is additive (rsync --update) — nothing local is ever deleted.
#
# Usage:
#   ./hermes_sync.sh                          # pick role by OS
#   HERMES_ROLE=consumer ./hermes_sync.sh     # force reader (pull+deploy)
#   HERMES_ROLE=author   ./hermes_sync.sh     # force writer (push)
#   HERMES_HOME=/home/user/.hermes ./hermes_sync.sh   # override live home
#
# Exit: 0 done / up-to-date, 1 error, 2 no portable snapshot present.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${HERMES_SYNC_REPO_ROOT:-$SCRIPT_DIR}"

log() { printf '[hermes-sync] %s\n' "$*"; }
die() { log "ERROR: $*"; exit 1; }

# ---------------------------------------------------------------------------
# 1) Detect OS -> role
# ---------------------------------------------------------------------------
OS_KIND="posix"
case "$(uname -s 2>/dev/null || echo Windows)" in
  MINGW*|MSYS*|CYGWIN*|Windows*|WINNT*) OS_KIND="windows" ;;
esac

ROLE="${HERMES_ROLE:-}"
if [[ -z "$ROLE" ]]; then
  if [[ "$OS_KIND" == "windows" ]]; then ROLE="author"; else ROLE="consumer"; fi
fi
log "role: $ROLE  (os=$OS_KIND, os_override=${HERMES_ROLE:-auto})"

case "$ROLE" in

# ---------------------------------------------------------------------------
# 2) AUTHOR / writer box: delegate to the Python backup script (PUSH).
# ---------------------------------------------------------------------------
  author)
    log "role=AUTHOR (writer) -> running hermes_backup.py"
    BACKUP_PY="$SCRIPT_DIR/hermes_backup.py"
    [[ -f "$BACKUP_PY" ]] || die "missing $BACKUP_PY (repo incomplete?)"
    # Pick a working Python interpreter. The `#!/usr/bin/env python3` shebang
    # is unreliable on MSYS/Windows, where only `python` may exist (not
    # `python3`), causing "python3: Permission denied".
    PY=""
    for cand in "${HERMES_PYTHON:-}" python3 python; do
      if [[ -n "$cand" ]] && command -v "$cand" >/dev/null 2>&1; then PY="$cand"; break; fi
    done
    [[ -n "$PY" ]] || die "no python3/python found on PATH to run the backup"
    # Give python a path it understands: on MSYS/Windows convert /c/... to a
    # native form (the native interpreter misreads /c/... as C:\c\...); leave
    # as-is on real Unix.
    if command -v cygpath >/dev/null 2>&1; then
      BACKUP_PY="$(cygpath -w "$BACKUP_PY")"
    fi
    "$PY" "$BACKUP_PY"
    exit $?
    ;;

# ---------------------------------------------------------------------------
# 3) CONSUMER box: refresh + deploy the portable subset locally (never push).
# ---------------------------------------------------------------------------
  consumer)
    log "role=CONSUMER (reader) -> pull + deploy portable config"
    # Resolve the LIVE Hermes home (Windows: LOCALAPPDATA; elsewhere ~/.hermes).
    if [[ "$OS_KIND" == "windows" ]]; then
      __appdata="${LOCALAPPDATA:-$HOME/AppData/Local}"
      LIVE_HOME="${HERMES_HOME:-$__appdata/hermes}"
    else
      LIVE_HOME="${HERMES_HOME:-$HOME/.hermes}"
    fi
    LIVE_HOME="${LIVE_HOME%/}"

    SNAPSHOT_DIR="$REPO_ROOT/state"
    log "snapshot : $SNAPSHOT_DIR"
    log "live home: $LIVE_HOME"
    [[ -d "$SNAPSHOT_DIR" ]] || die "no $SNAPSHOT_DIR under $REPO_ROOT — repo cloned/pulled?"

    # Refresh snapshot from the upstream AUTHOR (ff-only).
    if [[ -d "$REPO_ROOT/.git" ]]; then
      log "git pull (ff-only) from origin…"
      git -C "$REPO_ROOT" pull --ff-only origin \
        || die "pull failed (diverged?). Reconcile on the AUTHOR box, then re-run."
    else
      log "warn: $REPO_ROOT is not a git clone; deploying whatever snapshot is present."
    fi

    # Deploy ONLY the portable trees.
    PORTABLE_TREES=(SOUL.md skills memories cron)
    has_any=0
    for e in "${PORTABLE_TREES[@]}"; do [[ -e "$SNAPSHOT_DIR/$e" ]] && has_any=1; done
    (( has_any == 1 )) || die "portable snapshot empty/absent under $SNAPSHOT_DIR"

    for e in "${PORTABLE_TREES[@]}"; do
      src="$SNAPSHOT_DIR/$e"; [[ -e "$src" ]] || continue
      mkdir -p "$LIVE_HOME"
      if [[ -f "$src" ]]; then
        cp -f "$src" "$LIVE_HOME/$e"; log "  update  $e"
      elif [[ -d "$src" ]]; then
        mkdir -p "$LIVE_HOME/$e"
        if command -v rsync >/dev/null 2>&1; then
          rsync -a --update "$src/" "$LIVE_HOME/$e/"
        else
          cp -rp "$src/." "$LIVE_HOME/$e/"
        fi
        log "  sync    $e/ -> $LIVE_HOME/$e/"
      fi
    done

    log "done. portable config deployed to $LIVE_HOME."
    printf '%s\n' "NOTE: machine-local files (config.yaml, gateway_state.json," \
                  "channel_directory.json, caches) were NOT touched — they stay" \
                  "local to this box."
    exit 0
    ;;

  *) die "unknown HERMES_ROLE '$ROLE' (expected author|consumer)" ;;
esac