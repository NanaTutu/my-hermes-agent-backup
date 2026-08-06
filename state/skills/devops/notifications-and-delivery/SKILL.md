---
name: notifications-and-delivery
description: Send completion emails/notifications; verify sends landed.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [notifications, email, gmail, composio, verification, task-completion, telegram]
    related_skills: [hermes-mcp-integration, hermes-state-backup]
---

# Notifications & Delivery Verification

## Overview

Tutu frequently wants to be **notified when a long task completes** ("Update me when the task is completed. Send a mail on that to bohene8@gmail.com") — a completion email, a Telegram ping, or a backup push. This skill covers (a) the delivery channels that work on this setup and (b) the discipline of **verifying that a promised side-effect actually landed** before telling the user it did.

The most expensive failure mode: the assistant claims "email sent" but it never arrived — and the user has to come back and report it missing. Root causes: mid-turn output truncation can drop a tool call before it executes, or the send succeeded but landed in spam/latency. **Never assume; verify at the source.**

## Channels That Work (verified on Tutu's setup)

- **Gmail via Composio MCP** (Hermes-native bridge, no CLI): search tools → execute → confirm. Sender: `nana.tutu.paa.kwesi26@gmail.com` (connected Gmail account).
- **Telegram via `hermes send`**: works even when the gateway is down — used for back-online pings. `hermes send --to telegram "..."`.
- **GitHub backup push**: `C:\Users\bohen\hermes-backup\hermes_backup.py` commits + pushes state and sends a Telegram notification (see `hermes-state-backup` skill).

## Workflow: Send a Completion Email (Composio MCP → Gmail)

1. **Discover**: `mcp__composio__COMPOSIO_SEARCH_TOOLS` with `use_case: "send a Gmail email to someone"`, `known_fields: "recipient_email:bohene8@gmail.com"`, `session: {generate_id: true}`. Capture the returned `session_id` — pass it in ALL subsequent meta-tool calls.
2. **Send**: `mcp__composio__COMPOSIO_MULTI_EXECUTE_TOOL` with `tools: [{tool_slug: "GMAIL_SEND_EMAIL", arguments: {recipient_email, subject, body, is_html: false, user_id: "me"}}]` plus the `session_id`, `current_step`, and `sync_response_to_workbench: false`.
3. **Capture the handle**: the response returns `id` (message ID), `threadId`, and a `display_url` — keep them; they are your proof and your follow-up reference.
4. **Verify in Sent**: query `GMAIL_LIST_THREADS` with `query: "in:sent to:bohene8@gmail.com"` — confirm the new thread/snippet is present. Deliver the display_url to the user as the link.

## The "Email Did Not Show" Debug Path

When the user reports a promised email/notification missing:

1. **Do NOT immediately resend.** First verify whether it was ever dispatched:
   - Check Sent via `GMAIL_LIST_THREADS` (`in:sent to:<recipient>`) — the previous send may never have executed (e.g., the assistant's turn was truncated before the tool call ran, or the message was created as a draft and never sent).
2. **State the root cause honestly** (e.g., "the send call was dropped mid-turn; nothing was ever dispatched") — verified by the empty Sent query.
3. **Then send** per the workflow above and confirm the new message ID in Sent.
4. Check spam/latency only if Sent shows the message but the user still reports nothing received.

## Pitfalls

- **Mid-turn output truncation silently drops tool calls.** If a long response is cut by an output-length cap, the *next* tool call never executes — the user sees "I will send it now" with no email. Mitigation: put the send call FIRST in the turn, or verify Sent before claiming success.
- **Never claim a side-effect happened without a handle.** A message ID / commit SHA / thread URL is the only valid proof. If you don't have one, you didn't send it.
- **`web_extract` may be search-only** (DuckDuckGo backend) — curl + HTML stripping is the fallback for fetching pages (relevant when researching before writing notification content).
- **Session hygiene**: Composio workflows need the `session_id` from SEARCH_TOOLS in every subsequent call; starting a new use_case should generate a new session.

## User Preferences (do not re-ask)

- Completion notifications go to **bohene8@gmail.com**.
- Tutu wants the notification content to include a compact summary of what was completed and verified.
- "Update me when done" = send the notification AND report in chat — both, not either.

## Verification Checklist

- [ ] Send returned a message ID / thread URL (handle exists).
- [ ] Sent folder confirmed the message (Gmail) or process exit 0 + log (backup).
- [ ] User got both the chat update and the external notification.
