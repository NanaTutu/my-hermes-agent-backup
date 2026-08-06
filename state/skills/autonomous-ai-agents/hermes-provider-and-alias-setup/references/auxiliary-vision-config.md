# Configuring Hermes auxiliary vision (`auxiliary.vision`)

Session-verified recipe (2026-08, Windows host, opencode-zen default provider)
for making `computer_use(action="capture", mode="vision")` work when it
returns "No LLM provider configured for task=vision provider=auto. Run:
hermes setup".

## Why `auto` fails on key-less setups

`resolve_vision_provider_client()` with `provider: auto` only walks:

1. the main provider — but ONLY if its default model supports vision (a
   text-only default like `deepseek-v4-flash-free` is skipped);
2. the aggregator order `_VISION_AUTO_PROVIDER_ORDER = (openrouter, nous,
   deepinfra)` — each is key-gated (`OPENROUTER_API_KEY`, `NOUS_API_KEY`,
   `DEEPINFRA_API_KEY`). No key → no client → "Run: hermes setup".

So a machine with zero aggregator keys and a text-only main model needs an
EXPLICIT `auxiliary.vision.provider` + `.model`.

## Dead ends seen in practice (don't repeat)

- **openai-codex OAuth (chatgpt.com/backend-api/codex)**: client resolves,
  but the endpoint 400s on `image_url` — *"Model only supports text input;
  received unsupported content type 'image_url'"*. Text-first backend, even
  for gpt-5.5/gpt-5.2.
- **copilot with `GITHUB_TOKEN`**: resolves a client, but the API rejects the
  PAT — *"Personal Access Tokens are not supported for this endpoint"*. Needs
  a Copilot OAuth credential, not a classic PAT.
- **`gemini-3-flash` on opencode-zen**: routed fine but 401 `CreditsError` /
  "No payment method" — it's a PAID model on a free-tier account.

## Working recipe: free vision model on an already-authenticated provider

1. Discover provider's free model list (OpenAI-compatible):
   `curl -s "<base_url>/models" -H "Authorization: Bearer $<ENV_VAR>"` — free
   tiers show a `-free` suffix (e.g. `mimo-v2.5-free`, `ling-3.0-flash-free`,
   `deepseek-v4-flash-free`).
2. Pick a vision-capable free model. MiMo (`mimo-v2.5-free`) is known
   multimodal; when in doubt, look up the model family's capability.
3. Configure explicitly:
   ```
   hermes config set auxiliary.vision.provider opencode-zen
   hermes config set auxiliary.vision.model mimo-v2.5-free
   hermes config set auxiliary.vision.timeout 120
   ```
   (values shown are the verified-good ones on this host — substitute the
   user's provider/model; check `hermes config get auxiliary.vision`.)
4. Verify with `computer_use(action="capture", app="<app>", mode="vision")`:
   a healthy run returns `vision_analysis` with a real page description and
   `vision_analysis_routed_via: auxiliary.vision`.

## Notes

- `auxiliary.vision.base_url` / `api_key` left empty = profile defaults from
  the named provider are used (env var + plugin base_url).
- Model changes take effect on the next vision call; a mid-session "No LLM
  provider configured" right after `config set` is a config-race/reload
  artifact — retry the capture once before debugging.
- The same "explicit provider + model" pattern applies to other aux tasks
  (`auxiliary.web_extract`, `auxiliary.compression`, ...) that also fail on
  `auto` with no aggregator keys.
