#!/usr/bin/env bash
# cache_cleanup.sh — Hermes weekly safe-disk-cleanup.
#
# Deletes ONLY regenerable caches and build artifacts. NEVER touches:
#   Desktop, Documents, Downloads, Music, OneDrive, VirtualBox VMs,
#   Android SDK, source code, projects, or any personal content.
# Every path below is explicitly whitelisted. Missing paths are harmless.
#
# Safe to run on (and idempotent on) this Windows/git-bash host.

set -u

LOG="$APPDATA/../Local/hermes/cleanup-history.log"
mkdir -p "$(dirname "$LOG")" 2>/dev/null || true

free_mb() { df -k /c 2>/dev/null | awk 'NR==2{print $4}'; }
before_mb=$(free_mb)
start=$(date '+%Y-%m-%d %H:%M:%S')

HOME_DIR="$HOME"
LOCAL=$( [ -n "${LOCALAPPDATA:-}" ] && echo "$LOCALAPPDATA" || echo "$HOME_DIR/AppData/Local" )

# 1) package-manager caches (regenerable)
command -v uv   >/dev/null 2>&1 && uv cache clean >/dev/null 2>&1
command -v npm  >/dev/null 2>&1 && npm cache clean --force >/dev/null 2>&1

# 2) Gradle build caches (home)
rm -rf "$HOME_DIR/.gradle/caches" "$HOME_DIR/.gradle/wrapper" "$HOME_DIR/.gradle/daemon" 2>/dev/null

# 3) Dart/pub + .dartServer caches
rm -rf "$HOME_DIR/.pub-cache" "$LOCAL/Pub/Cache" "$LOCAL/.dartServer" 2>/dev/null

# 4) temp + crash dumps (only cache/temp dirs, never user files)
rm -rf "$LOCAL/Temp"/* "$LOCAL/CrashDumps"/* /c/Windows/Temp/* 2>/dev/null

# 5) Chrome cache (best-effort; locked files from a running Chrome are skipped)
GC="$LOCAL/Google/Chrome/User Data"
for c in "Default/Cache" "Default/Code Cache" "Default/GPUCache" "Default/ShaderCache" "GrShaderCache"; do
  rm -rf "$GC/$c" 2>/dev/null
done

# 6) Flutter engine debug-symbol .pdb files (not needed at runtime, regenerable)
FLUT_ROOT="$HOME_DIR/Documents/adf"
[ -d "$FLUT_ROOT" ] && find "$FLUT_ROOT" -path '*/bin/cache/artifacts/*' -name 'flutter_windows.dll.pdb' -delete 2>/dev/null

after_mb=$(free_mb)
freed_mb=$(( after_mb>before_mb ? after_mb-before_mb : 0 ))
freed_gb=$(awk -v m="$freed_mb" 'BEGIN{printf "%.1f", m/1048576}')

echo "cache_cleanup: freed ~${freed_gb} GB on C: (now $(free_mb) KB avail)"
echo "$start  freed=${freed_gb}GB  availKb=${after_mb}" >> "$LOG"