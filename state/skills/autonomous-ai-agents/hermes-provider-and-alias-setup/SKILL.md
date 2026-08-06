---
name: hermes-provider-and-alias-setup
description: "Add LLM providers and switchable model aliases in Hermes."
version: 1.0.0
author: Hermes Agent curator
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, providers, models, aliases, oauth, config, model-switching]
    related_skills: [hermes-agent]
---

# Hermes Provider & Model Alias Setup

Use when the user wants to add a model provider to Hermes (especially a
subscription-based account like ChatGPT/Plus/Pro, Claude, Copilot, Qwen,
MiniMax) or wire up switchable model aliases. The bundled `hermes-agent`
skill covers general config; this skill carries the exact auth flow, the
alias mechanism, and the pitfalls discovered in practice.

## Hard rules

- Never hand-edit `config.yaml` for the user — always `hermes config set KEY VAL`.
- Secrets go in `.env` / auth store, never in config.yaml.
- Check `hermes auth list` before and after any credential change.

## Provider discovery

- Installed provider profiles: `plugins/model-providers/<slug>/` under the
  hermes-agent source dir (e.g. `openai-codex`, `nous`, `qwen-oauth`).
- Provider table (auth type, env var): see hermes-agent skill
  `references/providers-and-models.md`. Subscription accounts use **OAuth**
  providers (openai-codex, qwen-oauth, minimax-oauth, nous); pay-per-token
  accounts use API-key providers (openrouter, anthropic, deepseek, ...).
- Auth command shape: `hermes auth add <provider>` (optional `--no-browser`,
  `--label`, `--timeout`). OAuth providers run a device flow: it prints a
  URL + code and blocks waiting for sign-in.

## Procedure: add a subscription (OAuth) provider

1. `hermes auth add <provider>` — run in BACKGROUND (it blocks on sign-in).
2. Poll the process (`process action=poll`) to read the device URL + code;
   relay both to the user. Code expires, so don't stall.
3. User authorizes in browser → process exits with
   `Added <provider> OAuth credential #1`.
4. Verify: `hermes auth list` shows the new credential (marked with `←`).
5. Test end-to-end BEFORE wiring aliases:
   `hermes chat -q "reply with exactly: OK" --provider <provider> -m <real-model-id>`.
   If this returns a reply, the credential + backend are good.

## Aliases (switchable, keep default intact)

User wants "available to switch sometimes" → add an alias, DON'T change
`model.default` / `model.provider`.

- Add: `hermes config set model.aliases.<name> <provider>/<model-id>`
  (e.g. `hermes config set model.aliases.chatgpt openai-codex/gpt-5.5`).
- Verify the yaml: `model.aliases.<name>` sits under the `model:` section.
- Verify resolution: `python -c "from hermes_cli.model_switch import resolve_alias; print(resolve_alias('<name>','<current-provider>'))"`.
- Switch in-session: `/model <name>` (session-scoped; `--global` persists as
  default). Switch back with `/model <original-default>`.
- Find the real model IDs a provider can serve: inspect the models cache
  `models_dev_cache.json` (dict keyed by vendor → `models` dict), or run
  `hermes model` (interactive picker — not scriptable).

## PITFALL: `-m <alias>` does NOT resolve user aliases

`hermes chat -q "..." -m <alias>` passes the alias string LITERALLY to the
backend (HTTP 401 `Model <alias> is not supported`). User aliases resolve
only via the interactive `/model <name>` path and provider-aware switch
logic. To test an alias non-interactively, use the explicit form:
`hermes chat -q "..." --provider <provider> -m <real-model-id>`.
A literal `-m` failure is NOT evidence the alias is misconfigured — check
`resolve_alias()` output first.

## Pitfalls

- `hermes model list` is not a command — `hermes model` is an interactive
  picker. Don't script against it.
- Don't flip `model.default`/`model.provider` when the user only wants the
  model available occasionally — ask or default to the alias path.
- If the user's plan tier is unknown, ask which plan before pinning a model
  ID; tiers gate which models the OAuth backend accepts.

## Session detail

- ChatGPT/openai-codex walkthrough (exact commands, transcript of the
  literal-`-m` failure): `references/chatgpt-openai-codex-walkthrough.md`