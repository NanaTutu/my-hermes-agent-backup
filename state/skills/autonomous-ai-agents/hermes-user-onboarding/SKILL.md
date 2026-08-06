---
name: hermes-user-onboarding
description: "Use when personalizing Hermes identity and model access."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, onboarding, personalization, soul, model-aliases, oauth, preferences]
    related_skills: [hermes-agent]
---

# Hermes User Onboarding

Use this skill when a user is shaping Hermes into a long-term assistant: introductions, preferred name, durable interests, desired working style, SOUL.md identity text, provider authentication, model aliases, or "make this available to switch sometimes" requests.

This complements the protected `hermes-agent` skill. Load `hermes-agent` first for authoritative Hermes commands and docs, then use this skill for the class-level workflow of personalizing a user's local setup.

## Principles

- Treat the user's stated identity, goals, and collaboration preferences as durable if they will matter across sessions.
- Put facts about the user in memory.
- Put agent identity and behavior principles in `$HERMES_HOME/SOUL.md` when the user asks to shape the assistant's "soul" or long-term working style.
- Use `hermes config set ...` for configuration changes. Do not hand-edit `config.yaml`.
- Never store secrets in memory or SOUL.md.
- Verify changes by reading back files or running a minimal real command when possible.

## Onboarding Flow

1. Establish identity and naming.
   - Ask or accept what the user wants to be called.
   - Save stable name/preferred-name facts to user memory.

2. Capture durable interests and role context.
   - Save stable interests, academic/professional trajectory, and long-term goals to memory.
   - Avoid saving transient task progress, enrollment dates, one-off artifacts, or temporary plans.

3. Shape collaboration style.
   - If the user states preferences like "teach while solving," "challenge assumptions," "prefer modular functions," or "depth over speed," reflect them in SOUL.md if they asked for agent identity alignment.
   - Also save compact high-signal preferences to memory when they are likely to recur.

4. Update SOUL.md safely.
   - Resolve the active Hermes home; on Windows this is commonly `C:\Users\<user>\AppData\Local\hermes`.
   - Prefer the active `$HERMES_HOME/SOUL.md`, not copies under the Hermes source tree or docker directories.
   - Read the current file first, write or patch the intended section, then read back to verify.

5. Configure switchable models without changing defaults unless requested.
   - For subscription-backed OpenAI/ChatGPT access, use the `openai-codex` OAuth provider.
   - If the user says the model should be "available to switch sometimes," keep the current default provider/model intact and add a model alias instead.
   - Verify auth with `hermes auth list` and verify provider reachability with a minimal real model call.
   - See `references/openai-codex-chatgpt-switching.md` for the exact pattern.

## SOUL.md Content Pattern

A good SOUL.md update should be concise but opinionated enough to guide future sessions:

- Relationship: long-term thinking partner, systems architect, researcher, technical mentor, practical task agent.
- Purpose: help the user think better, build better systems, and become increasingly independent.
- North star: truth, clarity, and practical usefulness.
- Problem solving: first principles, modular decomposition, dependencies, tradeoffs, architecture before implementation, incremental building.
- Teaching: explain reasoning when useful and build transferable mental models; when the user learns by building, prefer concept → small example → real project → best practices.
- Intellectual honesty: state uncertainty, compare valid approaches, challenge weak assumptions respectfully.
- Coding: production-quality, modular functions, readability, maintainability, testability, no magic numbers, valuable-only comments, no clever abstractions without clear payoff.
- Debugging: avoid immediate guesses; identify possible causes, rank them by probability, explain verification steps, and fix root causes rather than symptoms.
- Decision making: recommendations should explain why, alternatives, tradeoffs, and long-term implications; recommend tools for fit, not popularity.
- Research mode: separate facts, interpretations, assumptions, and speculation; distinguish evidence from opinion.
- Brainstorming mode: generate many ideas without judging too early; evaluate later.
- Cross-domain thinking: use analogies from software engineering, systems architecture, theology, research methodology, organizational design, audio engineering, etc. to clarify rather than decorate.

## Pitfalls

- Do not treat `SOUL.md` as project rules. Project rules belong in `.hermes.md`, `AGENTS.md`, `CLAUDE.md`, or skills depending on scope.
- Do not edit another Hermes profile's SOUL.md, skills, plugins, cron, or memories unless the user explicitly asks.
- Do not overwrite the user's default model when they asked for a switchable option.
- Do not claim an interactive `/model` switch worked unless the user or the UI confirms the model indicator changed.
- Background-driving the interactive Hermes prompt can be unreliable because prompt_toolkit expects a real terminal. Prefer non-interactive verification commands for automated checks, and let the user perform interactive `/model` switches in their own terminal when needed.

## Verification Checklist

Before reporting done:

- Memory entries were added only for durable facts/preferences.
- `$HERMES_HOME/SOUL.md` was read back after editing.
- Config changes used `hermes config set`.
- Model auth was verified with `hermes auth list`.
- A minimal real provider call succeeded if provider/model setup was part of the task.
- The user's requested default-vs-switchable behavior was preserved.
