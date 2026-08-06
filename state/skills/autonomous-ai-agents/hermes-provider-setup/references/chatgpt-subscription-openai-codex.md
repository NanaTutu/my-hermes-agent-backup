# Worked example: adding a ChatGPT subscription to Hermes (Aug 2026)

Full real-world walkthrough of connecting a paid ChatGPT plan via the
`openai-codex` provider and making it switchable without changing the default.
Reproduce the successful parts; the pitfalls are flagged so you don't repeat the
dead ends.

## End state (what "done" looks like)

- `config.yaml` still has the prior default (e.g. `opencode-zen` /
  `deepseek-v4-flash-free`) — NOT changed.
- `model.aliases.chatgpt = openai-codex/gpt-5.5` added via `hermes config set`.
- `hermes auth list` shows two credentials:
  ```
  openai-codex (1 credentials):
    #1  openai-codex-oauth-1 oauth   device_code
  opencode-zen (1 credentials):
    #1  OPENCODE_ZEN_API_KEY api_key env:OPENCODE_ZEN_API_KEY
  ```

## Step-by-step

### 1. OAuth device flow (background + poll, not foreground)

```bash
hermes auth add openai-codex    # run with background=true
```
Poll the process output; it prints:
```
1. Open this URL in your browser: https://auth.openai.com/codex/device
2. Enter this code: BQVQ-HX1NM
Waiting for sign-in... (press Ctrl+C to cancel)
```
Hand URL + code to the user. Wait until output shows `Added openai-codex OAuth
credential #1`. The command exits on its own once the user authorizes. Poll with
`process(action='wait')` or repeated `poll` — it takes as long as the user takes.

### 2. Add the switchable alias

```bash
hermes config set model.aliases.chatgpt openai-codex/gpt-5.5
```
Verified result in config.yaml:
```yaml
model:
  default: deepseek-v4-flash-free
  provider: opencode-zen
  base_url: https://opencode.ai/zen/v1
  api_mode: chat_completions
  aliases:
    chatgpt: openai-codex/gpt-5.5
```

### 3. Verify end-to-end WITHOUT the picker

`hermes model` is interactive only — don't drive it. Direct verification:
```bash
hermes chat -q "reply with exactly: OK" --provider openai-codex -m gpt-5.5
# -> OK
```

## Pitfalls hit in this session

### `-m chatgpt` fails with 401; `--provider openai-codex -m gpt-5.5` works
```
$ hermes chat -q "..." -m chatgpt
   HTTP 401: Model chatgpt is not supported
```
Cause (confirmed in source):
- `cli.py` `__init__`: `self.model = model or _config_model` — the literal `-m`
  string is used as-is; aliases are NOT resolved on this path.
- `hermes_cli/model_switch.py::resolve_alias()` — alias lookup (incl. user
  `model_aliases:` and `model.aliases:`) only runs in the interactive
  `/model` / provider-switch path.
So: alias resolves in-session via `/model chatgpt`, but the CLI flag needs the
real model id + provider.

### 2. `models_dev_cache.json` shape isn't what you'd guess
- Top-level keys = provider slugs (`openai`, `deepseek`, ...).
- `entry["models"]` is a DICT keyed by model id, NOT a list:
  - `len(list)` on the list path misleads; probe keys with `sorted(entry["models"].keys())`.
  - Model ids seen under `openai` (Aug 2026): `gpt-5 ... gpt-5.6`, `gpt-5-mini/nano/
    pro`, `gpt-5.2-chat-latest/codex`, `o3`, `o4-mini`, `codex-1`, etc.
- Confirm the provider field lands on the right catalog slug before filtering.

### 3. Interactive REPL can't be driven via raw PTY
Piping `/model chatgpt` into `hermes` through `background=true` + `pty=true` +
`process(submit)` just queues the line in the input buffer; the status bar never
updates and no model call fires. prompt_toolkit `\r` vs `\n`. The clean handling
is
`process(action='kill')` + telling the user to run `/model chatgpt themselves in their
own terminal (or use tmux).

## Notes on plan / subscription tiers
- Subscription tier decides which models are available — ask the user which plan
  (Plus/Pro/"Go") before pinning a default, because it changes the model id.
- Using `--provider` + `-m` pair for one-shots is the reliable non-interactive path;
  do not use `-m <alias>` and expect it to switch provider.