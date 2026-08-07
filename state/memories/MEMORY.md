Telegram gateway active on Tutu's Hermes: platform creds are env-var driven via .env at C:\Users\bohen\AppData\Local\hermes; TELEGRAM_ALLOWED_USERS=806045604 and TELEGRAM_HOME_CHANNEL=806045604 (Tutu's Telegram user ID == DM chat id); edits take effect via `hermes gateway restart`; `hermes send --to telegram` reaches the DM and works without a running gateway.
§
GitHub Hermes config backup = SINGLE-WRITER: the box = AUTHOR, only writer (hermes_backup.py auto-push; repo github.com/NaTutu/my-hermes-agent-backup.git; model in repo README). Linux box = CONSUMER: git pull then ./hermes_sync.sh copies only portable trees (SOUL, skills, memories, cron) to ~/.hermes; NEVER push back. config.yaml/gateway_state.json/channel_directory.json/caches stay machine-local; on merge conflicts keep THIS machine's values. Recent divergence fix.
§
Hermes aux vision: opencode-zen/mimo-v2.5-free (free vision model; gemini-3-flash paid; codex/copilot reject images).
§
cua-driver 0.18: stale 'session has ended' -> drive CLI direct (start_session+get_window_state). Exness demo ~$50 (verify footer; user may misstate). SL/TP: set_value on Edit (click field first); fresh Confirm token.
§
Tutu wants FX trading competency in Hermes: fx-trading skill lives at skills/trading/fx-trading/ + SOUL 'Trading Mode' section; trading mentorship is a recurring topic.
§
Double-check email dispatches actually landed (Gmail Sent folder) before confirming — one send was silently lost mid-turn.
§
CV/PDF ATS-safety audit via PyMuPDF: flag fonts outside ATS-safe set, body<10pt, name>20pt, margins<0.5in, images/tables; margins from span bboxes. Windows lacks pip -> use `uv venv` + `uv pip install --python ./.cvvenv/Scripts/python.exe pymupdf`.
§
TCL TV (tutu @172.20.10.3): volume ONLY via Cast (ADB keyevents don't move output volume; use `status`+`volume 0..1`, read back to confirm). Cast=castenv\tcl_tv.py @8009; ADB=adb.exe -s 172.20.10.3:5555 remote/screencap; skill tcl-tv-cast-control.
§
Composio via MCP: mcp_servers.composio + Bearer ${MCP_COMPOSIO_API_KEY}; mcp_composio_*; gateway restart + new session.