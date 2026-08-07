Telegram gateway active on Tutu's Hermes: platform creds are env-var driven via .env at C:\Users\bohen\AppData\Local\hermes; TELEGRAM_ALLOWED_USERS=806045604 and TELEGRAM_HOME_CHANNEL=806045604 (Tutu's Telegram user ID == DM chat id); edits take effect via `hermes gateway restart`; `hermes send --to telegram` reaches the DM and works without a running gateway.
§
GitHub Hermes config backup = SINGLE-WRITER: the box = AUTHOR, only writer (hermes_backup.py auto-push; repo github.com/NaTutu/my-hermes-agent-backup.git; model in repo README). Linux box = CONSUMER: git pull then ./hermes_sync.sh copies only portable trees (SOUL, skills, memories, cron) to ~/.hermes; NEVER push back. config.yaml/gateway_state.json/channel_directory.json/caches stay machine-local; on merge conflicts keep THIS machine's values. Recent divergence fix.
§
TTS works on Tutu's Telegram setup: edge provider (default) delivers playable voice bubbles. Tested and confirmed working.
§
Hermes aux vision: opencode-zen/mimo-v2.5-free (free vision model; gemini-3-flash paid; codex/copilot reject images).
§
cua-driver 0.18: fresh som-token per click/type; Chrome text_input needs foreground (bg drops for Chrome_WidgetWin_1); stale 'session has ended' → kill cua-driver.exe/recapture. On web broker term (Exness): click by element-index not raw coords (raw coords mis-scale ~1.6x); set SL+TP before clicking Buy/Sell and verify echoed pips/USD; pair pid+window_id.
§
Composio in Hermes via MCP: mcp_servers.composio endpoint + Authorization: Bearer ${MCP_COMPOSIO_API_KEY}; tools prefixed mcp_composio_*; need gateway restart + new session to load.
§
Tutu wants FX trading competency in Hermes: fx-trading skill lives at skills/trading/fx-trading/ + SOUL 'Trading Mode' section; trading mentorship is a recurring topic.
§
Double-check email dispatches actually landed (Gmail Sent folder) before confirming — one send was silently lost mid-turn.
§
CV/PDF ATS-safety audit via PyMuPDF: flag fonts outside ATS-safe set, body<10pt, name>20pt, margins<0.5in, images/tables; margins from span bboxes. Windows lacks pip -> use `uv venv` + `uv pip install --python ./.cvvenv/Scripts/python.exe pymupdf`.