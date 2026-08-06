---
name: hermes-provider-setup
description: "Add an OAuth or API-key model provider to Hermes."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, providers, oauth, model-aliases, chatgpt, openai-codex, configuration]
    related_skills: [hermes-agent]
---

# Hermes Provider Setup: subscription OAuth + switchable aliases

Companion to the bundled `hermes-agent` skill (protected — do not edit it; keep
session-derived provider learnings here). Use when the user wants to add a
subscription-based model service (ChatGPT Plus/Pro/Go, SuperGrok, etc.) or any
new provider to Hermes, and especially when they want it **available to switch
to** without replacing their current default model.

## Key facts

- **ChatGPT subscription → provider id `openai-codex`** (api_mode `codex_responses`,
  base_url `https://chatgpt.com/backend-api/codex`). Auth is OAuth device flow:
  `hermes auth add openai-codex`. Confirmed working end-to-end Aug 2026.
- OAuth providers: `nous`, `openai-codex`, `qwen-oauth`, `minimax-oauth` (device
  flow via `hermes auth add <provider>`); `copilot` uses a GitHub token. API-key
  providers just need `<NAME>_API_KEY` in `.env` (e.g. `OPENROUTER_API_KEY`,
  `DEEPSEEK_API_KEY`) — see the providers table in the hermes-agent skill.
- `hermes model` is an **interactive picker** — cannot be driven headless. For
  non-interactive changes use `hermes config set` (never hand-edit config.yaml;
  a stray indent can corrupt the file and break the live gateway).
- User model aliases: `hermes config set model.aliases.<name> <provider>/<model>`.
  Slash form = `provider/model` (DirectAlias); no slash = current provider.
  Use in-session with `/model <name>`, back with `/model <default-model-id>`.

## Switchable-alias recipe (keep current default)

```bash
hermes auth add openai-codex          # device flow; run in background, poll for URL+code
hermes auth list                       # verify credential registered
hermes config set model.aliases.chatgpt openai-codex/gpt-5.5
```

OAuth device flow: run the command in background, poll output for the
`https://.../device` URL and code, hand them to the user, then wait for
`Added <provider> OAuth credential` in the output before proceeding.

## PITFALL: the `-m` CLI flag does NOT resolve aliases

`hermes chat -q ... -m chatgpt` sends the literal string `chatgpt` to the backend
→ `HTTP 401: Model chatgpt is not supported`. User aliases (and built-in aliases)
resolve only through the interactive `/model <alias>` / provider-switch path
(`hermes_cli/model_switch.py::resolve_alias()`); the CLI init path assigns
`self.model = model` verbatim (`cli.py`). For one-shot CLI use, pass the explicit
pair instead:

```bash
hermes chat -q "your prompt" --provider openai-codex -m gpt-5.5
```

Built-in aliases (`gpt5`, `o3`, `codex`, `sonnet`, ...) resolve against the
**current** provider's catalog — to pin a model to a different provider, always
define a user alias with the `provider/model` slash form.

## Verify end-to-end (no picker)

```bash
hermes chat -q "reply with exactly: OK" --provider openai-codex -m gpt-5.5
hermes auth list
hermes doctor
```

## Enumerate available models headlessly

Read `$HERMES_HOME/models_dev_cache.json` (Windows:
`C:\Users\<user>\AppData\Local\hermes\models_dev_cache.json`). Top-level keys are
provider slugs; `entry["models"]` is a **dict keyed by model id, not a list** —
iterate its keys. Refresh with `hermes model --refresh`.

## PITFALL: don't automate the interactive REPL via raw PTY

Do NOT try to drive `/model` (or any command) by piping into `hermes` through a
background PTY + process submit — prompt_toolkit's `\r` vs `\n` handling makes
input queue in the buffer without executing, and the status bar never updates.
Use tmux (see hermes-agent skill) or let the user type the command in their own
terminal. Killing the hung session is the correct cleanup; don't fake a result.

## References

- `references/chatgpt-subscription-openai-codex.md` — full worked example: device
  flow transcript, cache structure probe, source-level confirmation of alias behavior.