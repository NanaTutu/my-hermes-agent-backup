Telegram gateway creds in .env at C:\Users\bohen\AppData\Local\hermes; TELEGRAM_ALLOWED_USERS=806045604, TELEGRAM_HOME_CHANNEL=806045604 (user ID==DM chat); restart via `hermes gateway restart`; `hermes send --to telegram` works without a live gateway.
§
GitHub Hermes config backup = SINGLE-WRITER: the box = AUTHOR, only writer (hermes_backup.py auto-push; repo github.com/NaTutu/my-hermes-agent-backup.git; model in repo README). Linux box = CONSUMER: git pull then ./hermes_sync.sh copies only portable trees (SOUL, skills, memories, cron) to ~/.hermes; NEVER push back. config.yaml/gateway_state.json/channel_directory.json/caches stay machine-local; on merge conflicts keep THIS machine's values. Recent divergence fix.
§
Hermes aux vision: opencode-zen/mimo-v2.5-free (free vision model; gemini-3-flash paid; codex/copilot reject images).
§
Exness demo ~$50 (verify footer; user may misstate). Church rig: Behringer WING fullsize (FW 3.1, "Potters-Arena"), skill behringer-mixer-scenes validated against real CHURCH.snap.
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
§
Home machine internet = Tutu's phone hotspot; when he leaves, machine goes offline. api.telegram.org 'DNS failure' spikes = hotspot drops, NOT resolver bugs. Gateway self-heals ~5min after network returns. Fibre broadband planned.