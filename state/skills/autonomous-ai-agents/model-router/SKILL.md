---
name: model-router
description: "Use when routing a task to the best opencode-go model."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, models, routing, opencode-go, aliases]
---

# Model Router (OpenCode Go)

Pick the best opencode-go model for the task the user just asked for, then act
on it. Backed by the OpenCode Go catalog snapshot (25 Aug 2026) and the
semantic `/model` aliases configured in `config.yaml` under `model.aliases`.

## When this applies

Any time the user gives a task and the best model is NOT the current one.
Classify the intent first, then route. Always prefer a recommendation (one
word) over silently switching — you cannot flip your own session model from
inside a turn; the switch lives at the session level.

## Routing table (alias -> model -> intent)

| `/model` alias | model | Best for |
|---|---|---|
| default | deepseek-v4-pro | general default; deep reasoning + coding |
| code | qwen3.8-max | frontier agentic coding, hard/long-horizon tasks |
| repo | kimi-k2.7-code | dedicated repo-scale coding agent (multi-file, end-to-end) |
| fast | gpt-5.6-luna | high-volume interactive + agent loops, fast general |
| flash | deepseek-v4-flash | fast/cheap reasoning, near-Pro quality at low cost |
| vision | kimi-k3 | multimodal: images + video input |
| eye | mimo-v2.5 | vision on a budget (omnimodal, cost-efficient) |
| write | minimax-m2.5 | creative writing, long-form prose |
| long | kimi-k2.5 | very long documents / corpora, deep analysis |
| cheap | hy3 | cheap tool-calling agents (Tencent Hunyuan 3) |
| reason | grok-4.5 | cost-effective near-frontier reasoning |
| chatgpt | openai-codex/gpt-5.5 | OpenAI Codex (separate provider) |

## How to route

1. **Recommend (default).** Tell the user the exact command, e.g.
   `/model code` — one word, works in CLI, gateway, and hermesUI. Then wait;
   they switch, and the task runs on the right model.
2. **One-shot execute.** If the task is self-contained and the user wants you
   to just do it, run it on the right model via subprocess:
   `hermes chat -q -m qwen3.8-max -Q "<task>"` (use `-Q` quiet mode).
   This is the only true "auto-route" for a single turn.
3. **Programmatic classify.** `python route_model.py "<prompt>"` prints the
   model + alias + matched keywords. Script lives at
   `~/AppData/Local/hermes/scripts/route_model.py` (`--list` shows the table).

## Classification rules (ordered)

Match in this order; first hit wins. If uncertain, default to deepseek-v4-pro.

1. **vision** — image/photo/screenshot/video/diagram/chart/OCR keywords
2. **write** — story/poem/essay/creative/narrative/lyrics
3. **long** — analyze/summarize/report on/audit/pdf/corpus/research
4. **code** — implement/refactor/debug/PR/api/sql/schema/deploy/build
5. **repo** — long-horizon/multi-file/codebase-wide/end-to-end agentic coding
6. **fast** — quick/one-liner/ping/status/list/translate/simple
7. **reason** — prove/math/logic/puzzle/first-principles/theorem
8. default — deepseek-v4-pro

## Pitfalls

- You **cannot** switch your own session model mid-turn; `/model` is a user
  slash command. Never claim you switched it — say which to run, or run a
  one-shot via `hermes chat -q -m`.
- The rule-based classifier is approximate. When the intent is ambiguous,
  surface the ambiguity and ask, rather than guessing.
- On the $10/mo plan cost is flat across models; the real constraint is the
  per-5-hour request quota (tight on frontier models). Don't burn `code`/
  `vision` on trivial tasks — use `fast`/`flash`/`cheap` for volume.
- Free/preview models (ox-alpha-free, hy3-preview) can vanish; don't route
  production work to them.
- The catalog drifts; re-check `curl -s https://opencode.ai/zen/go/v1/models`
  (with OPENCODE_GO_API_KEY) if an alias stops resolving.
