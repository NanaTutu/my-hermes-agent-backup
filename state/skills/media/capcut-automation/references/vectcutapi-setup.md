# VectCutAPI — install, wire into Hermes, and test (verified on CapCut 9.2.0.3931)

VectCutAPI (github.com/sun-guannan/VectCutAPI, a fork of ashreo/CapCutAPI) is a
Python project that generates CapCut/JianYing drafts LOCALLY via the bundled
`pyJianYingDraft` library. It has two entry points:

- `capcut_server.py` — Flask HTTP API (localhost:9001).
- `mcp_server.py` — native MCP server over stdio (self-contained, in-process
  imports; no HTTP server or cwd/PYTHONPATH needed).

The cloud (`open.capcutapi.top`, `fcapp.run`, OSS upload) is used only by the
`pattern/` demos and `download_script`/cloud-render paths — the core
create/add/save flow is local.

## Install (Windows, git-bash, uv; no pip on PATH)

```bash
cd ~/Documents/Hermes
git clone --depth 1 https://github.com/sun-guannan/VectCutAPI.git
cd VectCutAPI
uv venv .venv
uv pip install --python .venv/Scripts/python.exe -r requirements.txt -r requirements-mcp.txt
```

`requirements.txt` = imageio, psutil, flask, requests, oss2, json5. The MCP
extras add `mcp`, `aiohttp`, `pydantic`.

## config.json (the critical format mapping)

CapCut 9.x uses `draft_content.json` (NOT the legacy `draft_info.json`).
The profile that writes `draft_content.json` is `jianying_pro_10`, but that
profile defaults `is_capcut_env=False` (JianYing/`lv` metadata). For CapCut
international, set BOTH so you get the right file format AND CapCut (`cc`)
metadata:

```json
{
  "draft_profile": "jianying_pro_10",
  "is_capcut_env": true,
  "port": 9001,
  "is_upload_draft": false
}
```

`settings/local.py` applies `draft_profile` first, then lets `is_capcut_env`
override the flag without changing the profile. Sanity check: `GET /get_font_types`
returning `CC_*` font names confirms the CapCut env is active.

## API payloads (Flask)

- `POST /create_draft` `{width, height}` → `output.draft_id`
- `POST /add_video` `{draft_id, video_url, start, end, width, height}` —
  `video_url` may be a LOCAL absolute path (downloader.py copies it).
- `POST /add_text` `{draft_id, text, start, end, size, color}` (size is the
  font size; default font is 文轩体 which is missing → CapCut falls back).
- `POST /save_draft` `{draft_id, draft_folder}` — synchronous; copies the
  template dir, downloads/copies media into `assets/`, writes content JSON.
- Save runs `ffprobe` for metadata; it is NOT installed → non-fatal, material
  duration stays 0 and CapCut re-derives on open.

## Wire into Hermes (stdio MCP)

```bash
printf 'Y\n' | hermes mcp add vectcut \
  --command "C:/Users/bohen/Documents/Hermes/VectCutAPI/.venv/Scripts/python.exe" \
  --args "C:/Users/bohen/Documents/Hermes/VectCutAPI/mcp_server.py"
```

- `--command`/`--args` take ABSOLUTE paths (Hermes launches from its own cwd).
- The `Enable all 11 tools? [Y/n/select]` prompt wedges on non-interactive
  stdin — pipe `printf 'Y\n' |` (same class as the password-prompt pitfall).
- Verify: `hermes mcp list` shows `vectcut ... ✓ enabled`; tools load in a NEW
  session. Config lands in `~/AppData/Local/hermes/config.yaml` (command+args).

## Register a generated draft into CapCut (round-trip)

1. Copy `output/<draft_id>` → `.../com.lveditor.draft/<name>`.
2. Fix the video material `duration` (µs) and `path` (point at the draft's
   `assets/video/...`) in `draft_content.json` + mirrors + `Timelines/*/...`.
3. Append an entry to `root_meta_info.json` (draft_id = fresh UUID, draft_name,
   draft_fold_path, draft_json_file, tm_draft_create/modified µs, tm_duration,
   tm_draft_removed 0, draft_is_invisible false) and set draft_ids.
4. Relaunch CapCut. Proof: CapCut rewrites `draft_content.json` (shrinks it,
   back-fills video width/height/duration from the real file) — that rewrite is
   the success signal, stronger than a screenshot.

## Gotchas seen live

- `subprocess.check_output(['ffprobe', ...])` raises FileNotFoundError but is
  caught → logs "ffprobe command not found", continues. Not a blocker.
- `hermes mcp add` prints the tool list then "Cancelled." if stdin is not
  interactive — always pipe `Y`.
- The `draft_url` in every response is `https://www.install-ai-guider.top/...`
  (leftover ashreo fork domain) — ignore for local work.
