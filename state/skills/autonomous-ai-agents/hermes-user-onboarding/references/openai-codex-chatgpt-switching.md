# OpenAI Codex / ChatGPT Subscription Switching

Use this reference when a user has a ChatGPT subscription and wants ChatGPT models available inside Hermes without replacing their existing default provider/model.

## Pattern

1. Load the protected `hermes-agent` skill and the providers/models reference first for current commands.
2. Add the OAuth credential:

```bash
hermes auth add openai-codex
```

The command starts an OpenAI device-code OAuth flow. The user must complete it in the browser with the ChatGPT-subscribed account.

3. Verify the credential:

```bash
hermes auth list
```

Expected shape includes an `openai-codex` OAuth credential. Do not record tokens or device codes in memory or skills.

4. Preserve the existing default if the user says the model should be switchable or available sometimes.

Do not change:

```yaml
model.default
model.provider
```

5. Add a user alias instead:

```bash
hermes config set model.aliases.chatgpt openai-codex/gpt-5.5
```

Use whatever concrete model is appropriate for the user's plan and current catalog. In the observed setup, `gpt-5.5` worked through `openai-codex`.

6. Verify alias resolution if needed with Hermes internals or by using `/model chatgpt` interactively. The direct CLI flag path may pass a user alias literally in some versions, so prefer an explicit provider/model pair for non-interactive tests:

```bash
hermes chat -q "reply with exactly: OK" --provider openai-codex -m gpt-5.5 --no-restore-cwd
```

A successful response proves the OAuth credential and provider route work.

## User-Facing Instructions

Inside an interactive Hermes session:

```text
/model chatgpt
```

To return to the previous default, switch back by model name or use the model picker. If the user confirms the status bar changed, accept that as the interactive switch verification.

For one-shot calls without changing the default:

```bash
hermes chat -q "your prompt" --provider openai-codex -m gpt-5.5
```

## Pitfalls

- Do not promise that ChatGPT becomes the default when the user asked for a switchable option.
- Do not use or store API keys for this path; it is OAuth device-code auth.
- Do not capture device codes or auth URLs as durable memory.
- Do not claim `/model chatgpt` worked unless the user or UI confirms the model indicator changed.
- If background PTY driving of interactive Hermes does not submit commands cleanly, do not encode that as a permanent tool failure. Use explicit non-interactive verification and let the user perform the interactive switch in their own terminal.
