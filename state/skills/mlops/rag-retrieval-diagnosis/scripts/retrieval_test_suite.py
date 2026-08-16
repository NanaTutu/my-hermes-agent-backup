#!/usr/bin/env python3
"""Graded RAG retrieval test suite (engine-agnostic; RAGFlow example).

Regress a retrieval pipeline by intent class. Each test is tagged with a class
and a gold-standard target (the expected unit number). Run retrieval ONLY (no
LLM) and print PASS/MISS plus the rank and vector-vs-term split.

Usage:
    python retrieval_test_suite.py

Edit CONFIG below (base URL, dataset id, API key source) and the TESTS list.
For RAGFlow, the key can live in a local .env with RAGFLOW_API_KEY=... (or
override _load_key). For other engines, rewrite retrieve() to hit their API.
"""
import json
import os
import re
import urllib.request

# ── CONFIG ────────────────────────────────────────────────────────────────────
BASE = "https://ragflow.kennyken.top"
DATASET_ID = "5cdc8f04966811f192565be544c79fb5"   # replace with your dataset id
TOP_N = 8
VECTOR_WEIGHT = 0.3   # match the engine's configured vector_similarity_weight

def _load_key() -> str:
    env = os.environ.get("RAGFLOW_API_KEY")
    if env:
        return env
    for line in open(os.path.join(os.path.dirname(__file__), ".env")):
        if line.startswith("RAGFLOW_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("set RAGFLOW_API_KEY (env or .env)")
# ─────────────────────────────────────────────────────────────────────────────

def retrieve(question: str, top: int = TOP_N):
    body = {
        "question": question,
        "dataset_ids": [DATASET_ID],
        "page": 1, "page_size": top,
        "similarity_threshold": 0.0,
        "vector_similarity_weight": VECTOR_WEIGHT,
        "top_k": 1024,
    }
    req = urllib.request.Request(BASE + "/api/v1/retrieval",
                                 data=json.dumps(body).encode(), method="POST")
    req.add_header("Authorization", "Bearer " + _load_key())
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0 Safari/537.36")
    req.add_header("Accept", "application/json")
    d = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
    out = []
    for c in d.get("data", {}).get("chunks", []):
        out.append({
            "head": c.get("content", "").strip().split("\n")[0][:50],
            "sim": round(c.get("similarity", 0), 3),
            "vec": round(c.get("vector_similarity", 0), 3),
            "term": round(c.get("term_similarity", 0), 3),
        })
    return out

def article_of(head: str):
    m = re.match(r"Article\s+(\d+)", head)
    return int(m.group(1)) if m else None

# ── TEST DEFINITIONS: (class, query, {gold-standard article numbers}) ─────────
TESTS = [
    ("exact-identifier", "What does Article 10 say?", {10}),
    ("exact-identifier", "What is Article 10?", {10}),
    ("title", "What is the title of Article 10?", {10}),
    ("semantic", "Which article deals with interpretation of parental citizenship?", {10}),
    ("semantic", "Which article deals with citizenship of a parent who died before the birth of a person?", {10}),
    ("exact-identifier", "Tell me about Article 1.", {1}),
    ("exact-identifier", "What does Article 9 provide?", {9}),
    ("clause", "What does Article 10(2) provide?", {10}),
    ("cross-reference", "Which article does Article 10 refer to for registration?", {9, 10}),
]
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"{'class':<16} {'query':<66} target  hit@rank  top8-heads")
    print("-" * 140)
    for cls, q, target in TESTS:
        res = retrieve(q)
        hits = [(i + 1, c) for i, c in enumerate(res) if article_of(c["head"]) in target]
        hit = "HIT@" + "/".join(str(r) for r, _ in hits) if hits else "MISS"
        heads = " | ".join((c["head"][:16] if c["head"] else "?") for c in res[:TOP_N])
        print(f"{cls:<16} {q[:66]:<68} {str(sorted(target)):<7} {hit:<9} {heads}")
        if hits:
            r, c = hits[0]
            print(f"{'':16} {'':68} {'':7} -> rank {r}: sim={c['sim']} vec={c['vec']} term={c['term']}")
