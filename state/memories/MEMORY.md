Telegram gateway active on Tutu's Hermes: platform creds are env-var driven via .env at C:\Users\bohen\AppData\Local\hermes; TELEGRAM_ALLOWED_USERS=806045604 and TELEGRAM_HOME_CHANNEL=806045604 (Tutu's Telegram user ID == DM chat id); edits take effect via `hermes gateway restart`; `hermes send --to telegram` reaches the DM and works without a running gateway.
§
GitHub Hermes config backup = SINGLE-WRITER: the box = AUTHOR, only writer (hermes_backup.py auto-push; repo github.com/NaTutu/my-hermes-agent-backup.git; model in repo README). Linux box = CONSUMER: git pull then ./hermes_sync.sh copies only portable trees (SOUL, skills, memories, cron) to ~/.hermes; NEVER push back. config.yaml/gateway_state.json/channel_directory.json/caches stay machine-local; on merge conflicts keep THIS machine's values. Recent divergence fix.
§
TTS works on Tutu's Telegram setup: edge provider (default) delivers playable voice bubbles. Tested and confirmed working.
§
Hermes aux vision: auxiliary.vision.provider=opencode-zen, model=mimo-v2.5-free (only free vision-capable model on Tutu's key; gemini-3-flash is PAID; codex OAuth & GITHUB_TOKEN copilot routes reject images).
§
cua-driver 0.18: fresh som-capture token needed per click/type; Chrome text_input needs foreground delivery (background dropped for Chrome_WidgetWin_1). Stale sessions error 'this session has ended' — kill cua-driver.exe / new capture respawns. Video in Chrome tab doesn't steal focus.
§
Composio in Hermes via MCP: mcp_servers.composio = https://connect.composio.dev/mcp, header Authorization: Bearer ${MCP_COMPOSIO_API_KEY} (both Bearer & x-consumer-api-key accepted; key in .env). 7 meta-tools prefixed mcp_composio_* (SEARCH_TOOLS, MULTI_EXECUTE_TOOL, MANAGE_CONNECTIONS...). Gmail connected; GitHub deferred. MCP tools need gateway restart + new session to load.
§
Tutu wants FX trading competency in Hermes: fx-trading skill lives at skills/trading/fx-trading/ + SOUL 'Trading Mode' section; trading mentorship is a recurring topic.
§
Double-check email dispatches actually landed (Gmail Sent folder) before confirming — one send was silently lost mid-turn.