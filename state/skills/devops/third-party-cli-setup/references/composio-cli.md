# Composio CLI — Windows reality & the connect flow

Session-verified (2026-08, Windows host). Asked to run the Composio dashboard's
setup commands (`curl -fsSL https://composio.dev/install | bash` + `composio
login`) and "help connect".

## The blocker: no native Windows support

- Official `INSTALL.md` / docs list supported platforms as **Linux x64, Linux
  ARM64, macOS Intel, macOS Apple Silicon** only.
- The `curl | bash` installer hard-aborts on Windows: *"error: Windows is not
  supported. Use WSL ... and run this script inside your WSL distribution."*
- It is a known open GitHub issue (ComposioHQ/composio #3057, #3134) — do not
  expect it to change soon.

## npm trap: `composio` is a decoy

`npm view composio` → version **1.0.0**, *"UI Components for the web"*, author
`flashcodx` — an unrelated 2019/2020 library squatted on the name, NOT the
Composio AI CLI. Installing it silently succeeds (`added 1 package`) and the
binary is absent (`composio: command not found`). The real tooling is under the
scoped `@composio/*` packages (e.g. `@composio/client`, `@composio/openclaw-plugin`).
**Uninstall the squat if you fell for it:** `npm uninstall -g composio`.

## The install that DOES work (Linux/macOS, or WSL)

Official installer respects env vars, e.g.:

```bash
curl -fsSL https://composio.dev/install | bash
```

Options: `COMPOSIO_INSTALL_SHELL=none` (install only, touch no shell files),
`COMPOSIO_INSTALL_DIR`, `COMPOSIO_BIN_DIR`, `COMPOSIO_INSTALL_VERSION`.
Manual path: download `composio-linux-x64.zip` / `-aarch64` / `-darwin-*` from
GitHub Releases and copy the FULL bundle (the CLI reads support files beside
the exe — never copy only the nested `composio` binary). verify with
`composio --version`; `composio login` is a browser OAuth flow.

## Chosen fallback on native Windows (Option 1, no CLI)

The dashboard already logs the user in as their Composio account. Connect
apps purely through the web UI (`Home → Connect Apps`): pick a tile, hit
Connect, complete the provider's own OAuth in the browser. No CLI, no admin,
no reboot. Alternatives if a CLI is truly required: WSL install (admin +
distro, possibly reboot) or the Python SDK (`uv` present where pip isn't) keyed
from a dashboard-generated API key.

## Useful dashboard/valid-URL facts

- Valid dashboard root: `https://dashboard.composio.dev` (works, redirects into
  the user's workspace). Deep workspace URLs carry a per-workspace slug that
  varies and 404'd when reconstructed by hand — open the root and click
  through rather than guessing the slug.
- App catalog shows "Active" vs "Connect" per app (e.g. Gmail may already be
  Active; GitHub/Google Calendar/Sheets/Drive commonly start unconnected).
- `Connect` on a third-party app opens THEIR OAuth page — the end-user
  authorize step cannot be automated; plan for user action.