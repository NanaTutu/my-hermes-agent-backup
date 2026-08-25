#!/usr/bin/env python3
"""route_model.py — classify a prompt/task and recommend the best opencode-go model.

Rule-based (no LLM, no network): keyword/pattern matching against the
OpenCode Go routing table. Deterministic, free, instant.

Usage:
    python route_model.py "build me a FastAPI auth service"
    python route_model.py "what does this screenshot show"
    echo "write a short story" | python route_model.py
    python route_model.py --list

Output: the recommended model, the /model alias to switch, and the matched
category + keywords (so you can see why and override).

The table below mirrors the OpenCode Go model guide (snapshot 25 Aug 2026).
"""
from __future__ import annotations

import sys

# Alias -> (model, description). Order = priority for first-match classification.
ROUTES: list[tuple[str, str, str, tuple[str, ...]]] = [
    # (category, alias, model, keyword triggers)
    ("vision", "vision", "kimi-k3",
     ("image", "photo", "picture", "screenshot", "video", "diagram", "chart",
      "scan", "ocr", "look at", "visual", "see this", "clip", "thumbnail",
      "frame", "logo", "poster", "flyer")),
    ("write", "write", "minimax-m2.5",
     ("story", "poem", "essay", "creative", "narrative", "screenplay", "lyrics",
      "song", "fiction", "novel", "write a", "write me", "blog post", "script for")),
    ("long", "long", "kimi-k2.5",
     ("long document", "analyze", "summarise", "summarize", "report on", "audit",
      "review the", "many files", "codebase-wide", "full codebase", "pdf",
      "corpus", "research", "paper", "compare", "evaluate")),
    ("code", "code", "qwen3.8-max",
     ("implement", "refactor", "fix the bug", "debug", "pull request", "pr review",
      "repo", "repository", "function", "endpoint", "api", "sql", "query",
      "schema", "migrate", "deploy", "test suite", "unit test", "lint", "ci",
      "pipeline", "docker", "build a", "feature", "backend", "frontend", "flutter",
      "php", "fastapi", "database")),
    ("repo", "repo", "kimi-k2.7-code",
     ("long-horizon", "multi-file", "codebase", "drive the repo", "agent to",
      "end-to-end", "from scratch project", "scaffold")),
    ("fast", "fast", "gpt-5.6-luna",
     ("quick", "fast", "one-liner", "ping", "status of", "list the", "translate",
      "simple", "just check", "what time")),
    ("reason", "reason", "grok-4.5",
     ("prove", "math", "logic", "puzzle", "first principles", "derive", "theorem",
      "formal", "think through", "reason about", "explain why")),
]

DEFAULT = ("default", "default", "deepseek-v4-pro")


def classify(text: str) -> tuple[str, str, str, str]:
    """Return (category, alias, model, matched_keywords)."""
    t = " " + text.lower() + " "
    for category, alias, model, keywords in ROUTES:
        hits = [k for k in keywords if (" " + k + " " if " " in k else k) in t
                or k in t]
        # keyword match: substring, but require word-ish boundaries for short words
        if hits:
            return category, alias, model, ", ".join(hits[:4])
    return DEFAULT[0], DEFAULT[1], DEFAULT[2], "no strong signal"


def list_routes() -> None:
    print("OpenCode Go routing table (snapshot 25 Aug 2026):")
    print(f"  /model default  -> deepseek-v4-pro   (general default)")
    for category, alias, model, _ in ROUTES:
        print(f"  /model {alias:<8}-> {model:<22} ({category})")
    print("\nManual aliases (secondary picks within a category):")
    for alias, model, note in (
        ("flash", "deepseek-v4-flash", "fast/cheap reasoning"),
        ("eye", "mimo-v2.5", "vision on a budget"),
        ("cheap", "hy3", "cheap tool-calling agents"),
    ):
        print(f"  /model {alias:<8}-> {model:<22} ({note})")
    print("\nOne-shot run:  hermes chat -q -m <model> -Q \"<task>\"")


def main() -> None:
    if "--list" in sys.argv or "-l" in sys.argv:
        list_routes()
        return
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args:
        text = " ".join(args)
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        list_routes()
        print("\nNo prompt given. Pass a task as an argument or pipe one via stdin.")
        return

    category, alias, model, hits = classify(text)
    print(f"prompt:   {text.strip()[:120]}")
    print(f"category: {category}")
    print(f"matched:  {hits}")
    print(f"model:    {model}")
    print(f"switch:   /model {alias}")
    print(f"one-shot: hermes chat -q -m {model} -Q \"{text.strip()[:200]}\"")


if __name__ == "__main__":
    main()
