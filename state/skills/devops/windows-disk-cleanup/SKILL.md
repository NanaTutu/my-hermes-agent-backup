---
name: windows-disk-cleanup
description: "Free Windows disk space by reclaiming caches."
---

# Windows Disk Cleanup

Reusable method for reclaiming disk space on a Windows C: drive (MSYS/git-bash shell) without risking user data. Use when the user asks to free up space, map free space, find big files or folders, or reduce disk pressure.

## Mindset: three tiers of deletability
Classify every candidate removal by tier, not by wish.
- REGENERABLE (auto-clean, no consent): tool caches and build artifacts that re-download on next use — uv/npm/pip/Dart/Gradle caches, temp, Chrome cache, crash dumps, debug .pdb symbols, SDK cache.
- REDUNDANT / REDOWNLOADABLE (consent-gated, then removable): duplicate copies kept side-by-side, old installer media (.iso, setup installers), old SDK/system images. Reversible in spirit (re-download or keep one copy), but they are files the user chose to keep.
- CONTENT (NEVER auto-delete): personal documents, VMs (vdi), media, music, source projects, OneDrive data. Erasing these without an explicit yes is data loss. When in doubt, keep.

## Durable rules learned
- Keep a CLOUD-BACKED copy when deleting duplicates: if an archive exists in both plain `Documents` and `OneDrive\Documents`, delete the plain copy and keep the OneDrive (synced) copy — a copy survives even if the guess is wrong.
- Do NOT delete a real VM disk, personal media, or downloads without explicit confirmation.
- Some session caches are locked while an app is open (Chrome `Default/Cache`); `Code Cache`/`GPUCache`/`ShaderCache` clear fine live.

## Step 1 — map the disk fast (never `du -d1` on Windows/MSYS)
`du -d1` across a profile reliably times out (~60s) because it stats every file. Use a Python `os.scandir` scanner — an order of magnitude faster, with a wall-clock budget and expecting `.git`/`node_modules` to be skipped.
Bundled probes:
- `scripts/disk_scan.py <root>` — per-child sizes (GB), with `AppData/Local` children broken out separately.
- `scripts/find_large.py <root>` — individual files >100MB sorted by size to surface the real large files behind a bulky folder.

## Step 2 — reclaim regenerable caches (safe, do first)
- Package caches: `uv cache clean`; `npm cache clean --force`; pip cache if present.
- Gradle: `rm -rf ~/.gradle/caches ~/.gradle/wrapper ~/.gradle/daemon` — regenerates on next build; often the single biggest win.
- Dart/Flutter: `~/.pub-cache`, `AppData/Local/Pub/Cache`, `AppData/Local/.dartServer`, plus Flutter SDK `*.pdb` under `flutter/bin/cache/artifacts/**` (debug symbols not needed at runtime).
- Temp/dumps: contents of `AppData/Local/Temp`, `AppData/Local/CrashDumps`, `/c/Windows/Temp`.
- Chrome: `AppData/Local/Google/Chrome/User Data/{Default/Cache,Default/Code Cache,GPUCache,ShaderCache,GrShaderCache}`.
Prefer the tool's own clean subcommand over `rm -rf`. Record `df -h /c | tail -1` BEFORE and AFTER so the real delta is proven.

## Step 3 — content tier: find it, then ASK
Sum remaining big categories and present them with sizes. Ask via a multi-select (max 4 choices) listing the top items, and state what will NOT be touched. If a confirmation times out, apply the conservative filter: erase ONLY regenerable and provably-redundant items — keep all content, VMs, cloud copies, media. Report exact removed and kept.

## Pitfalls
- Never `rm -rf` on a guessed path — test `[ -e "path" ]` first (paths have spaces/parentheses; quote everything).
- Do not trust per-child `du`; use `df` before/after for real value.
- Data-safety-sensitive: content tier is irreversible — default is keep-and-ask, and disclosing exactly what was removed is mandatory.