Telegram gateway active on Tutu's Hermes: platform creds are env-var driven via .env at C:\Users\bohen\AppData\Local\hermes; TELEGRAM_ALLOWED_USERS=806045604 and TELEGRAM_HOME_CHANNEL=806045604 (Tutu's Telegram user ID == DM chat id); edits take effect via `hermes gateway restart`; `hermes send --to telegram` reaches the DM and works without a running gateway.
§
GitHub state backup: Tutu wants significant Hermes state changes committed/pushed to backup repo + Telegram notify. Windows box: on-session-finalize 'hermes-backup' plugin -> C:\Users\bohen\hermes-backup\hermes_backup.py -> github.com/NanaTutu/my-hermes-agent-backup.git. Linux box: repo cloned at /home/tutu/my-hermes-agent-backup; restore = copy state/* into $HERMES_HOME (secrets excluded: .env/auth.json/state.db); hermes-backup plugin ACTIVE there (on_session_finalize, GITHUB_TOKEN in .env, backup.log in mirror). gh CLI authed as NanaTutu (keyring).
§
TTS works on Tutu's Telegram setup: edge provider (default) delivers playable voice bubbles. Tested and confirmed working.
§
Hermes aux vision: auxiliary.vision.provider=opencode-zen, model=mimo-v2.5-free (only free vision-capable model on Tutu's key; gemini-3-flash is PAID; codex OAuth & GITHUB_TOKEN copilot routes reject images).
§
cua-driver 0.18: fresh som-capture token needed per click/type; Chrome text_input needs foreground delivery (background dropped for Chrome_WidgetWin_1). Stale sessions error 'this session has ended' — kill cua-driver.exe / new capture respawns.
§
Composio in Hermes via MCP: mcp_servers.composio = https://connect.composio.dev/mcp, header Authorization: Bearer ${MCP_COMPOSIO_API_KEY} (both Bearer & x-consumer-api-key accepted; key in .env). 7 meta-tools prefixed mcp_composio_* (SEARCH_TOOLS, MULTI_EXECUTE_TOOL, MANAGE_CONNECTIONS...). Gmail connected; GitHub deferred. MCP tools need gateway restart + new session to load.
§
Tutu wants FX trading competency in Hermes: fx-trading skill lives at skills/trading/fx-trading/ + SOUL 'Trading Mode' section; trading mentorship is a recurring topic.
§
Double-check email dispatches actually landed (Gmail Sent folder) before confirming — one send was silently lost mid-turn.