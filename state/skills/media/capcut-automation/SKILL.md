---
name: capcut-automation
description: Automate CapCut video editing (GUI or draft-file/MCP).
---

# CapCut Automation

CapCut (ByteDance's consumer editor) has **no public API** for the desktop app.
Two working routes, in order of preference:

1. **Draft-file / MCP** (preferred) — manipulate CapCut's local JSON draft
   files directly, or drive VectCutAPI's local MCP server. Deterministic,
   structured, no GUI.
2. **GUI pixel-driving** (fallback) — Win32 screenshot + coordinate clicks.
   Covers anything clickable but is coordinate-fragile.

## Draft file format (CapCut 9.x)

- Projects live at:
  `C:\Users\<user>\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft\<draft_name>\`
- Each draft folder: `draft_content.json` (+ `.bak`, `template-2.tmp`,
  `template.tmp`), `draft_meta_info.json`, `Timelines/<id>/`,
  `timeline_layout.json`, media under `assets/`.
- Index: `.../com.lveditor.draft/root_meta_info.json` → `all_draft_store[]`.
  Each entry needs `draft_id` (UUID), `draft_name`, `draft_fold_path`,
  `draft_json_file` (path to `draft_content.json`), `draft_root_path`,
  `tm_draft_create`/`tm_draft_modified` (µs), `tm_duration`, `tm_draft_removed: 0`,
  `draft_is_invisible: false`. Set `draft_ids` = len(all_draft_store).
- To register a new draft: copy the folder in, append the entry, bump draft_ids.
  **Proof of success**: CapCut rewrites `draft_content.json` on open (it
  normalizes + back-fills video width/height/duration from the real file).
  A malformed draft is left untouched or marked removed.
- CapCut 9.x uses the `draft_content.json` format (NOT the older
  `draft_info.json`). VectCutAPI's matching profile is `jianying_pro_10`
  (see references/vectcutapi-setup.md).

## VectCut MCP tools (`mcp__vectcut__*`)

11 tools, called via `tool_call` (find with `tool_search`, schema via
`tool_describe`). Order: `create_draft` → `add_*` → `save_draft`.

- `create_draft` — width, height → returns `draft_id`
- `add_video` — `video_url` (REQUIRED; LOCAL path ok), draft_id, start, end,
  width, height, duration, transition, volume, speed, mask/transform params
- `add_audio` — audio_url, draft_id, start, end, volume, fade_in, fade_out
- `add_image` — image_url, draft_id, start, end, position_x, position_y,
  scale, rotation
- `add_text` — draft_id, text (REQUIRED), start, end, size, color, font
- `add_subtitle` — draft_id, srt_content, font_size, font_color
- `add_effect` — draft_id, effect params (enum names via the HTTP get_*_types)
- `add_sticker` — draft_id, sticker params
- `add_video_keyframe` — draft_id, property_types, times, values
- `get_video_duration` — video_url (needs ffprobe → prefer explicit `duration`)
- `save_draft` — draft_id, draft_folder (optional) → writes `draft_folder/<draft_id>`

For the registration step (copy into CapCut + index entry), use
`scripts/register_draft.py --src <draft_id dir> --name <name>` instead of
hand-editing — it copies, fixes media paths/durations (photo→assets/image/,
video→assets/video/, audio→assets/audio/), and upserts the index. Then run
`scripts/fix_capcut92.py --draft "<projects>/<name>"` — WITHOUT this second
step CapCut 9.2 refuses to open the draft ("unusual path"); see the Pitfalls
section and references/capcut-9.2-compat.md.

## GUI pixel-driving (fallback)

- CapCut is a Qt6 app (window class `Qt622QWindowIcon`) — its UIA tree is
  unresponsive, so cua-driver `computer_use` element-index clicks time out.
  Drive by raw pixels instead.
- **Launch**: `cmd.exe /c start "" "C:\Users\<user>\AppData\Local\CapCut\Apps\CapCut.exe"`.
  `explorer.exe "<path>"` returned exit 1 in git-bash (unreliable); `cmd start`
  is the dependable way. A direct bash/git-bash spawn of the exe crashes with
  an EGL/GPU error on Intel-UHD-only machines, so always go through the shell.
- Win32 recipe (PowerShell `Add-Type` P/Invoke):
  1. `SetForegroundWindow(hwnd)` (precede with the Alt press/release trick to
     release the foreground lock) + `ShowWindow(SW_RESTORE)`.
  2. `System.Drawing.Graphics.CopyFromScreen` → PNG.
  3. `vision_analyze` the cropped window region → element coordinates.
  4. `SetCursorPos` + `mouse_event` (LEFTDOWN/LEFTUP) at those screen coords.
  5. Re-screenshot to verify the click landed before the next step.
- This drives the REAL cursor (foreground), unlike cua-driver's background
  cursor. Window move/resize breaks saved coordinates — re-read the rect each
  time (GetWindowRect via P/Invoke, or EnumWindows).

## Pitfalls

- **CapCut 9.2 rejects VectCutAPI drafts: "project is from an unusual path".**
  Root cause is NOT draft-specific: the `jianying_pro_10` template stamps
  `platform.app_source="lv"` (JianYing) + `new_version="110.0.0"`, but native
  CapCut 9.2 writes `app_source="cc"`, `app_id=359289`, `app_version="9.2.0"`,
  `new_version="181.0.0"` (+ device/hard-disk/mac ids). CapCut treats a
  foreign-app ("lv") draft as invalid, so EVERY registered draft fails until
  `scripts/fix_capcut92.py --draft "<projects>/<name>"` rewrites
  platform/last_modified_platform/new_version and fills `path:""`,
  `draft_type:"video"`, `canvas_config.background:null`. Note:
  `config.json`'s `is_capcut_env:true` does NOT fix this — it only toggles the
  material export format, not the `platform` dict (which comes from
  `profile.platform`). Diagnose via `draft_content.json["platform"]["app_source"]`.
  Full field diff: references/capcut-9.2-compat.md.
- **ffprobe absent on this box** → VectCutAPI's save step logs
  "ffprobe command not found" but it is NON-FATAL: video material duration
  stays 0 and CapCut re-derives width/height/duration from the file on open.
  Do not treat the missing probe as a blocker.
- **add_video accepts LOCAL file paths** — downloader.py checks
  `os.path.exists(url)` and copies instead of doing HTTP. No need to serve a
  test file over HTTP.
- The MCP server (`mcp_server.py`) is self-contained: in-process imports plus
  `sys.path.insert(0, dirname(abspath(__file__)))`, so wiring into Hermes needs
  no HTTP server, no cwd, no PYTHONPATH.
- VectCutAPI returns a leftover cloud URL (`install-ai-guider.top`) in
  `draft_url` fields — cosmetic, ignore for local use.
- Default text font is `文轩体` (path `C:/文轩体.ttf`, nonexistent) — CapCut
  falls back to a default font; not fatal.
- **add_subtitle is broken out-of-the-box (3 bugs, all patched in the local
  VectCutAPI copy):** (1) `pyJianYingDraft/script_file.py::import_srt` never
  initializes `font_type` → `UnboundLocalError` "cannot access free variable
  'font_type'" when `font` is omitted. Fix: add `font_type = None` before the
  `if font:` block. (2) `add_subtitle_impl.py` defaults `vertical=True`
  (vertical CJK text) and `alpha=0.4` (40% opacity) — both wrong for
  horizontal English captions. Fix: `vertical: bool = False`, `alpha: float = 1.0`.
  (3) The MCP process holds these modules in memory once started, so a patch
  only takes effect in a FRESH process — inject subtitles via a standalone
  script (`Script_file.load_template` + `import_srt` + `dump`) rather than
  relying on the long-lived MCP after editing. Pass an explicit `font` member
  name (e.g. `"Poppins_Bold"`) to avoid the crash entirely.
- **add_image media paths are NOT written by save_draft:** images land in
  `materials.videos` as `type: "photo"` with `path: ""` and
  `remote_url: <source path>`; save_draft copies the file to
  `assets/image/<hashed>.png` (renames/transcodes to PNG) but leaves `path`
  empty. The audio material likewise has `path: ""` and `duration: 0`, and
  stores its filename under `name` (NOT `material_name`). register_draft.py
  now handles all three: photo→`assets/image/`, video→`assets/video/`,
  audio→`assets/audio/` (using `material_name or name`), and stamps zero
  durations. If a draft opens with black/missing media, check `path` first.

## Verification

- HTTP route: `POST /create_draft → /add_video → /add_text → /save_draft`,
  then confirm the output folder has `draft_content.json` + `assets/video/*.mp4`.
- Round-trip: copy+register the draft, relaunch CapCut, then confirm CapCut
  rewrote `draft_content.json` and filled in media dimensions (stronger than a
  screenshot).
- See references/vectcutapi-setup.md for the full install/wire/test recipe.
