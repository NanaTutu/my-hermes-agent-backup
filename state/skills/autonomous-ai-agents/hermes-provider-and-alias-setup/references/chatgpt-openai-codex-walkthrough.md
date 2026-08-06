# ChatGPT / openai-codex walkthrough

Real session transcript of adding a ChatGPT subscription (Plus/Pro/"Go"
tier) to Hermes as a switchable (non-default) model. Verified working.

## What the openai-codex provider is

- Plugin: `plugins/model-providers/openai-codex/plugin.yaml` →
  `name: openai-codex-provider`, base_url
  `https://chatgpt.com/backend-api/codex`, `api_mode: codex_responses`.
- It signs in with the user's OpenAI account (their existing ChatGPT
  subscription) via OAuth device flow — NOT a pay-per-token OpenAI API key.

## Commands actually run

1. Add credential (blocking device flow → background):
   `hermes auth add openai-codex`
   Poll via process tool. It prints:
   1. Open this URL in your browser: https://auth.openai.com/codex/device
   2. Enter this code: XXXX-XXXXX
   On success (user authorizes in browser): process exits
   `Added openai-codex OAuth credential #1: "openai-codex-oauth-1"`.

2. Verify: `hermes auth list`
   ```
   openai-codex (1 credentials):
     #1  openai-codex-oauth-1 oauth   device_code ←
   ```
   (`←` marks the picked/active credential.)

3. End-to-end test (before aliases):
   `hermes chat -q "reply with exactly: OK" --provider openai-codex -m gpt-5.5`
   Returned `OK` → backend + credential good.

4. Alias (keeps deepseek default intact):
   `hermes config set model.aliases.chatgpt openai-codex/gpt-5.5`
   Result yaml:
   ```yaml
   model:
     default: deepseek-v4-flash-free
     provider: opencode-zen
     base_url: https://opencode.ai/zen/v1
     api_mode: chat_completions
     aliases:
       chatgpt: openai-codex/gpt-5.5
   ```

5. Verify alias resolution:
   `python -c "from hermes_cli.model_switch import resolve_alias; print(resolve_alias('chatgpt','opencode-zen'))"`
   → `('openai-codex', 'gpt-5.5', 'chatgpt')`

## Model ID discovery

`models_dev_cache.json` at the Hermes home root: dict keyed by vendor slug,
each with a `models` dict of available model IDs. For openai this showed the
full gpt-5.x family up through gpt-5.6 (gpt-5.5, gpt-5.6, gpt-5.4-pro,
etc.). Use these real IDs for `-m` and for alias `<provider>/<id>` values.

## The literal-`-m` failure (KEY)

`hermes chat -q "reply with exactly: OK" -m chatgpt` FAILED with:
```
HTTP 401: Model chatgpt is not supported
💡 Your API key was rejected by the provider... Does your account have access to chatgpt?
```
Cause: the `-m` flag passes the string literally to the current provider's
backend and does NOT run `resolve_alias()`. The alias is only resolved by
the interactive `/model chatgpt` command and the provider-aware switch path.
Confirmation: `resolve_alias('chatgpt', ...)` returned the correct tuple, so
the alias was configured correctly all along — the test command was wrong.
Lesson: verify aliases with resolve_alias / the interactive `/model` switch,
not with `-m`.

## User preference (from this session)

User keeps deepseek (opencode-zen) as default; wants ChatGPT available to
SWITCH TO SOMETIMES, not as default. Do not flip `model.default` /
`model.provider` for such a request — add an alias instead.