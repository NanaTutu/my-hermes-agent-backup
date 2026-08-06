---
name: third-party-cli-setup
description: Install and auth third-party CLIs and agent integrations.
version: 1.0.0
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [cli, install, npm, curl-pipe-bash, oauth, agent-integrations, windows]
    category: devops
    related_skills: [windows-desktop-automation, hermes-provider-and-alias-setup]
---

# Third-Party CLI & Agent Integration Setup

Use when the user asks to install a third-party CLI tool or connect an
external agent-integration platform (Composio, MCP servers, n8n, OpenClaw,
etc.) to this machine. Captures the pitfalls of installing tools that ship
only a `curl | bash` installer, the npm name-squat trap, and how to reach the
same outcome without a CLI when the platform forbids the host OS.

## Sequence (verify BEFORE you install)

1. **Check platform support first, from the official docs.** Many CLIs are
   Linux/macOS-only and the installer aborts midway ("Windows is not
   supported"). Read the vendor's `INSTALL.md` / docs page before running
   anything: supported platforms table tells you instantly whether native
   Windows works, or whether you need WSL / a Docker image / a web fallback.
2. **Read the install script when it will execute as the user.** For
   `curl -fsSL <url> | bash`, at minimum know what the vendor's official
   method is. The approval gate may block remote-pipe-to-shell commands —
   expect it, and ask the user for explicit consent (they may pick
   "approve, but review the script first").
3. **If the vendor ships an npm package, verify its identity.** The bare
   package name on npm can be an unrelated squat: `npm install -g composio`
   installs a 2020 "UI Components" library by `flashcodx`, NOT the Composio
   AI CLI. Check `npm view <pkg>` (description, author, version) against the
   vendor, or search `npm search <name>` for the official scoped package
   (`@vendor/cli`, etc.). Installing the squat silently succeeds and leaves
   `command not found`.
4. **Prefer the official install command over a re-implementation.** If the
   official installer exists but refuses the host OS, do NOT improvise an
   equivalent from a different source — confirm with the vendor's docs what
   the supported alternative is (often: WSL, or the SDK/web dashboard).
5. **Verify after install:** `<cli> --version` or `<cli> --help` from a NEW
   shell — the entry point may not be on the current shell's PATH (npm
   global bin vs git-bash PATH). `command -v <cli>`.

## npm name-squat detection (quick recipe)

```bash
npm view <name>          # description + author reveal the squat immediately
npm search <name> --json | head -c 2000
```

Signals of a squat: description unrelated to the vendor ("UI Components for
the web"), version stuck at 1.0.0 for years, author not the vendor. The real
CLI usually lives under a scoped name or a dist-tag the docs reference.

## curl | bash consent flow

- The gate blocks `curl ... | bash` until the user approves. Ask once with
  clear options (run now / review script first / skip). Do not retry the
  same command on timeout — that is treated as acting without consent.
- If the installer aborts due to OS ("Windows is not supported"), report the
  exact error and pivot to the documented alternative — do not force it.

## Authentication / login step is interactive

`<cli> login` almost always opens a browser OAuth flow that blocks for user
action. Plan for it: run the CLI login with the user ready to click through,
or skip the CLI entirely when the same account works from the web dashboard
(generate an API key there and use the SDK instead).

## Windows-specific fallbacks (in priority order)

1. **Web dashboard / API key + SDK** — often enough; no install, no admin.
2. **WSL** — the vendor-sanctioned path when the CLI is Linux-only, but it
   needs admin + a distro install (possibly a reboot). Check `wsl --status`
   / `wsl --list --verbose` first; a bare `wsl.exe` binary with no distro is
   not a working WSL.
3. **SDK via uv** — `uv` is usually present where pip is not; SDKs often
   bundle the CLI's engine.

## Connecting the platform to Hermes via MCP (agent integration)

When the goal is *"Hermes should call the tool directly"* (not just install the
CLI), the clean path is often a vendor MCP server wired into Hermes's native
MCP client — no CLI needed at all on Windows. Sequence that worked:

1. Find the vendor MCP endpoint + auth from their docs (Composio:
   `https://connect.composio.dev/mcp`). **Probe it with curl BEFORE wiring** so
   you learn the auth scheme and confirm the key works:
   ```bash
   curl -s -w "\nHTTP %{http_code}\n" -X POST "$URL" \
     -H "Content-Type: application/json" \
     -H "Accept: application/json, text/event-stream" \
     -H "$AUTH_HEADER" \
     -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"probe","version":"1"}}}'
   ```
   HTTP 200 + a `serverInfo` result = auth works. Test every plausible header
   explicitly (`x-consumer-api-key:`, `Authorization: Bearer`, `x-api-key`).
2. Attach it to Hermes with `hermes mcp add <name> --url "$URL" --auth header`
   (see pitfalls below — the interactive prompt is flaky off a real TTY).
3. After add, tools register as `mcp_<name>_<tool>`, verified with
   `hermes mcp list`. Confirm the header template uses `Bearer ${MCP_<NAME>_API_KEY}`
   (a runtime-interpolated env ref) and the secret lives in the profile `.env`.
4. **MCP tools load at agent START — they only appear after**
   `hermes gateway restart` **+ a new session.** Tell the user this upfront so
   they expect the tools to be absent until then.

### Pitfalls (this exact flow)

- **The `hermes mcp add` interactive prompt is the flaky part, not the vendor.**
  On Windows, `input()`/password prompts over piped stdin and even background
  PTY wedge silently (60–90s timeouts, echoed input concatenating with the
  prompt). Don't fight it. Pre-seed the credential so the CLI skips the prompt:
  ```bash
  cd "$HERMES_HOME/hermes-agent" && python -c \
    "from hermes_cli.config import save_env_value; save_env_value('<NAME>','<KEY>'.upper(),'<KEY>')"
  ```
  then `printf 'Y\nY\n' | hermes mcp add <name> ...` — it prints
  `<ENV>: already configured` and proceeds; both remaining prompts (`auth? Y/n`
  and `enable all? Y/n/select`) accept `Y`. Check the exact env key name with
  `grep MCP_ <config.yaml>` / the `_env_key_for_server()` mapping (name → `MCP_<NAME>_API_KEY`).
- **Secret hygiene:** when the API key is shown on a logged-in dashboard A, don't
  ask the user to paste it into chat. Click the dashboard's **Copy**, then read
  it locally: `powershell -NoProfile -Command "Get-Clipboard"`. The secret never
  transits the messaging platform.
- **A 401 body like "No Authorization: Bearer ...** on request" is generic — it
  does NOT by itself prove Bearer is the required scheme. The vendor dashboard
  pages sometimes document a *different* header (`x-consumer-api-key`); probe
  each candidate and keep whichever returns 200.
- `hermes config set` is scalar-only and won't write the nested `mcp_servers`
  dict for you — use `hermes mcp add` (or the config file) for MCP entries, not
  `hermes config set`.

## Session detail

- Composio CLI (platform restriction, npm squat, dashboard connect flow,
  exact commands tried): `references/composio-cli.md`
- Hermes-native MCP wiring for a third-party platform (verify-then-wire,
  `mcp add` prompt workaround, gateway-restart requirement):
  `references/hermes-mcp-wiring.md`