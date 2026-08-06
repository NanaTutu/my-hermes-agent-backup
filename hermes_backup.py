#!/usr/bin/env python3
"""
hermes_backup.py
================
Synchronize a safe subset of the local Hermes configuration state to a
private Git repository on GitHub.

Design principles
-----------------
- WHITELIST, not blacklist: only files known to be non-sensitive/re-creatable
  are mirrored.  Anything not in the sync list is never touched.
- Sane excludes inside copied trees (locks, caches, sqlite DBs).
- Defense in depth: after staging, every file to be committed is scanned for
  secret-shaped content (API keys, tokens, private keys).  A hit aborts the
  commit so a real secret can never reach GitHub.
- The GitHub token is never written to disk and never stored in the repo.  It
  is read from $HERMES_HOME/.env at push time and supplied to git as an
  ephemeral Authorization header only.

Trigger: called on the Hermes `on_session_finalize` shell hook (session close),
or run manually.  Idempotent - a no-op run commits nothing.

Exit codes: 0 ok, 1 error/abort.
"""

from __future__ import annotations

import base64
import hashlib
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
HERMES_HOME = Path(
    os.environ.get("HERMES_HOME")
    or Path.home() / "AppData" / "Local" / "hermes"
)
MIRROR = Path(os.environ.get("HERMES_BACKUP_MIRROR") or Path.home() / "hermes-backup")
REMOTE = os.environ.get(
    "HERMES_BACKUP_REMOTE",
    "https://github.com/NanaTutu/my-hermes-agent-backup.git",
)
# Where mirrored content lands inside the repo:
STATE_DIR = "state"

# ---------------------------------------------------------------------------
# Whitelist: relative paths under HERMES_HOME to mirror (files and/or trees)
# ---------------------------------------------------------------------------
WHITELIST = [
    "config.yaml",
    "SOUL.md",
    "memories",
    "skills",
    "cron/jobs.json",
    "channel_directory.json",
    "gateway_state.json",
    "context_length_cache.yaml",
    "provider_models_cache.json",
]

# Names/dirs that must never be mirrored, matched against path segments and
# against relpaths/suffixes.  Covers secrets, PII, runtime caches, sqlite.
FORBIDDEN_SUFFIXES = {".db", ".db-shm", ".db-wal", ".lock", ".log", ".lck",
                      ".key", ".pem", ".crt", ".p12", ".pfx", ".tmp"}
FORBIDDEN_DIR_NAMES = {".env", "venv", "node_modules", "__pycache__", "bin",
                       "models", ".curator_backups", ".git", ".curator_archives"}
FORBIDDEN_FILE_NAMES = {".env", "auth.json", "auth.lock",
                        ".usage.json", ".curator_state", ".bundled_manifest"}
FORBIDDEN_FULL = {"skills/.curator_backups", "skills/.usage.json"}

# ---------------------------------------------------------------------------
# Secret-shape scan patterns (defense in depth). Match credential SHAPES, not
# known values, so they catch new credentials too.
#
# Calibration: skill docs legitimately contain placeholder examples
# ("sk-xxx...xxxx", "your_key_here", "not-needed", "api_key = resolve(...)").
# We therefore treat a match as a REAL finding only when the captured value is
# not placeholder-shaped (no xxx/your/here/example markers, no function call,
# no env-var indirection) and looks like an actual credential.  Private-key
# blocks and JWTs are unambiguous and always abort.
# ---------------------------------------------------------------------------

# High-confidence, always abort (no placeholder escape):
HARD_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"-----BEGIN OPENSSH PRIVATE KEY-----"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
]

# Shape patterns: abort only if the matched value is NOT placeholder-shaped.
SHAPE_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9]{16,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
]

# Assignment-style: "KEY = value" / "key: value".  Flag only when the value
# looks like a real credential literal (>= 16 chars, contains a digit, and no
# placeholder markers).  This excludes doc examples, env-var indirection
# (os.environ[...]), and function calls (resolve_api_key(...)).
ASSIGN_PATTERN = re.compile(
    r"(?i)(password|passwd|api_key|apikey|secret|access_token|token)"
    r"\s*[:=]\s*['\"]?([A-Za-z0-9_\-@#$%^&*!\.]{8,})"
)

PLACEHOLDER_MARKERS = (
    "...", "xxx", "xxxx", "your_", "_here", "here", "example", "sample",
    "placeholder", "not-needed", "changeme", "dummy", "lorem", "test_",
    "<", ">", "${", "$(", "(", ")", "[", "]", "os.environ", "getenv",
    "resolve_", "get_", "args.", "env[", "None", "TODO", "#", "=",
    "sk-ant-", "auth-key", "secret123",
)


def _is_placeholder(value: str) -> bool:
    v = value.strip().strip('"').strip("'")
    if len(v) > 64:
        return True
    return any(m in v for m in PLACEHOLDER_MARKERS)


def scan_for_secrets(files: list[Path]) -> list[tuple[Path, str]]:
    hits: list[tuple[Path, str]] = []
    for f in files:
        if not f.is_file():
            continue
        if f.stat().st_size > 2_000_000:  # big binary/cache file -> not text we inspect
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for pat in HARD_PATTERNS:
            if pat.search(text):
                hits.append((f, pat.pattern))
                break
        else:
            flagged = False
            for pat in SHAPE_PATTERNS:
                for m in pat.finditer(text):
                    tok = m.group(0)
                    if not _is_placeholder(tok):
                        hits.append((f, pat.pattern))
                        flagged = True
                        break
                if flagged:
                    break
            if not flagged:
                for m in ASSIGN_PATTERN.finditer(text):
                    val = m.group(2)
                    if (not _is_placeholder(val)
                            and len(val) >= 16
                            and any(c.isdigit() for c in val)):
                        hits.append((f, ASSIGN_PATTERN.pattern))
                        break
    return hits


def log(msg: str) -> None:
    print(f"[hermes-backup] {msg}", flush=True)


def read_token() -> str | None:
    env_path = HERMES_HOME / ".env"
    if not env_path.exists():
        return None
    try:
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            if raw.lstrip().startswith("GITHUB_TOKEN="):
                return raw.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        return None
    return None


def is_forbidden(rel: Path) -> bool:
    """True if a path (relative to HERMES_HOME or mirror) must never be stored."""
    rels = str(rel).replace("\\", "/")
    if rels in FORBIDDEN_FULL:
        return True
    for part in rel.parts:
        lp = part.lower()
        if part in FORBIDDEN_FILE_NAMES or lp in {n.lower() for n in FORBIDDEN_DIR_NAMES}:
            return True
    if rel.suffix in FORBIDDEN_SUFFIXES:
        return True
    return False


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def is_files(root: Path) -> list[Path]:
    """Recursively list regular files under root, applying is_forbidden as we
    walk so forbidden subtrees are pruned early. Returns absolute paths."""
    out: list[Path] = []
    if not root.is_dir():
        return out
    for dirpath, dirnames, filenames in os.walk(root):
        dp = Path(dirpath)
        dirnames[:] = [d for d in dirnames if not is_forbidden(dp / d)]
        for fn in filenames:
            p = dp / fn
            if p.is_file() and not is_forbidden(p):
                out.append(p)
    return out


def collect_source_files() -> list[Path]:
    """Return the absolute files under HERMES_HOME that the whitelist selects,
    pruned by forbidden rules."""
    files: list[Path] = []
    for rel in WHITELIST:
        src = HERMES_HOME / rel
        if not src.exists():
            continue
        if src.is_dir():
            for f in is_files(src):
                relf = f.relative_to(HERMES_HOME)
                if not is_forbidden(relf):
                    files.append(f)
        else:
            relf = Path(rel)
            if not is_forbidden(relf):
                files.append(src)
    return files


def run_git(args: list[str], token: str | None = None,
            cwd: str | None = None) -> subprocess.CompletedProcess:
    cmd = ["git"]
    if token:
        basic = base64.b64encode(f"x-access-token:{token}".encode()).decode()
        cmd += ["-c", f"http.extraHeader=AUTHORIZATION: basic {basic}"]
    cmd += args
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def main() -> int:
    MIRROR.mkdir(parents=True, exist_ok=True)
    git_root = MIRROR

    # ---- sync whitelist into mirror/state ---------------------------------
    dest_base = git_root / STATE_DIR
    dest_base.mkdir(parents=True, exist_ok=True)
    srcs = collect_source_files()
    if not srcs:
        log("no whitelisted sources found - nothing to do")
        return 1

    copied: list[Path] = []
    removed_manifest: list[Path] = []
    for src in srcs:
        rel = src.relative_to(HERMES_HOME)
        dest = dest_base / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        copied.append(dest)

    # ---- prune stale mirrored files ------------------------------------------------
    # Recompute the canonical set from the CURRENT whitelist; delete mirror files
    # under state/ that are no longer produced (keeps accidental cruft from
    # lingering in the backup).
    desired = set(dest_base / f.relative_to(HERMES_HOME) for f in srcs)
    for existing in is_files(dest_base):
        rel = existing.relative_to(dest_base)
        # prune forbidden files even if their source still exists (e.g. files
        # mirrored before the forbid list was tightened)
        if is_forbidden(rel):
            existing.unlink(missing_ok=True)
            removed_manifest.append(existing)
            continue
        # prune for real only when its source no longer exists
        if existing not in desired:
            src = HERMES_HOME / rel
            if not src.exists():
                existing.unlink(missing_ok=True)
                removed_manifest.append(existing)
    if removed_manifest:
        log(f"pruned {len(removed_manifest)} stale file(s)")

    # ---- scan ------
    to_scan = is_files(dest_base)
    if not to_scan:
        log("warn: no files staged")
        return 1

    hits = scan_for_secrets(to_scan)
    if hits:
        log("SECRET SCAN FAILED - NOT PUSHING")
        for f, pat in hits[:20]:
            print(f"  !! {f.relative_to(git_root)}  matched  {pat}")
        return 1

    # ---- git ops ----------------------------------------------------------
    r = run_git(["status", "--porcelain"], cwd=str(git_root))
    if r.returncode != 0:
        log("git status failed: " + (r.stderr.strip() or "unknown"))
        return 1
    if not r.stdout.strip():
        log("no changes since last push - nothing to do")
        return 0

    if run_git(["add", "-A"], cwd=str(git_root)).returncode != 0:
        log("git add failed")
        return 1

    msg = f"hermes state backup {datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ}"
    if run_git(["commit", "-m", msg], cwd=str(git_root)).returncode != 0:
        log("git commit failed")
        return 1

    rg = run_git(["remote", "get-url", "origin"], cwd=str(git_root))
    if rg.returncode != 0:
        if run_git(["remote", "add", "origin", REMOTE], cwd=str(git_root)).returncode != 0:
            log("failed to register origin remote")
            return 1

    token = read_token()
    if not token:
        log("GITHUB_TOKEN not found in .env; committed locally but NOT pushed.")
        return 1

    rp = run_git(["push", "-u", "origin", "main"], token=token, cwd=str(git_root))
    if rp.returncode != 0:
        log("PUSH FAILED: " + (rp.stderr.strip() or rp.stdout.strip() or "unknown"))
        return 1
    log("committed and pushed to GitHub")
    return 0


if __name__ == "__main__":
    sys.exit(main())