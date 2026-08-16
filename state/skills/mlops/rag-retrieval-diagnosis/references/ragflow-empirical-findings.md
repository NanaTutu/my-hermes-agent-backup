# RAGFlow-specific findings (verified against a live v0.26.4 instance)

Context: hosted instance `https://ragflow.kennyken.top` (user has account-only access, no server control). Dataset "1992 Constitution Ghana": 2 documents, chunk_method=naive, chunk_token_num=128, delimiter `"\n\n\n\n`#``##`"`, embedding `qwen3-embedding:0.6b`, LLM `phi4:14b`. 341 chunks for the constitution doc (roughly one article per chunk).

## metadata_condition schema (HTTP API)

The chat/retrieval API takes a per-request `metadata_condition`:

```json
{"logic": "and", "conditions": [{"name": "unit_number", "comparison_operator": "=", "value": "10"}]}
```

Operators seen in docs/API: `=` / `is`, `not contains`. The Chat UI additionally offers "Automatic / Semi-automatic / Manual" filtering modes (Automatic = LLM extracts the value from the query, then applies the same filter).

## Metadata filtering is FILE-level, not chunk-level (proven)

Test on the single-file constitution dataset:
- `metadata_condition {unit_number="10"}` → returned Articles 32, 36, 19 (NOT Article 10).
- `metadata_condition {unit_number="999"}` (value in no document) → returned nothing.

Interpretation: "999" discarded the whole document; "10" kept the whole document (its array contains "10"), then semantic ranking ran inside it and still failed. RAGFlow's own release notes: "It filters out irrelevant FILES." So a metadata filter cannot isolate an article inside a single file.

## The metadata is document-level, not per-chunk

Document `meta_fields` shape: `unit_number` = LIST of 293 values, `unit_title` = LIST of 184, `unit_type` = LIST of 6 (DeepDOC "built_in_metadata" / layout recognition — one parallel array per field, mismatched lengths are a symptom of guessing at unmarked structure).

Chunk keys (from `/chunks`): `available, content, dataset_id, docnm_kwd, document_id, id, image_id, important_keywords, positions, questions, tag_kwd` — **no unit_number**. So the field the user needs to disambiguate is not on the chunk.

## Retrieval weight formula

`similarity = vector_similarity_weight * vector_similarity + fulltext_weight * term_similarity`. Verified exactly on real scores (e.g. 0.3×0.628 + 0.7×0.103 = 0.260). Default/current: vector 0.30 / full-text 0.70.

## Worked test result (the pattern to recognize)

Graded suite, top-N=8, threshold 0.0, weights 0.3/0.7:

| class | query | result |
|---|---|---|
| exact-id | What does Article 10 say? | MISS (32/36/19/31/106…) |
| exact-id | What is Article 10? | MISS (rank1 = "Section 10 — PUB") |
| title | What is the title of Article 10? | MISS |
| exact-id | Tell me about Article 1. | MISS (rank has "Section 2 — FIRS") |
| exact-id | What does Article 9 provide? | MISS |
| clause | What does Article 10(2) provide? | MISS |
| cross-ref | Which article does Article 10 refer to? | MISS |
| semantic | …interpretation of parental citizenship? | HIT @ rank 1 (vec 0.838) |
| semantic | …parent who died before the birth… | HIT @ rank 1 (vec 0.885) |

Semantic path works (vector carries it); every locator-class query fails. "Article 10" even collides with "Section 10" chunks — identifier ambiguity in the raw data.

## Chunking behavior (naive)

The delimiter `"\n\n\n\n`#``##`"` means a section boundary is 4+ newlines OR a `#`/`##` heading line. The naive chunker keeps a section WHOLE (chunk_token_num is a merge target, not a hard split) — which is why the ~1500-token Article 19 survived as one chunk. Plain-text "Article N" lines are NOT recognized as headings (only `#`/`##` are), so chunk boundaries fall back to blank-line heuristics — fragile. Proper `## Article N` / `### TITLE` headings make boundaries deterministic.

## Local bridge / locator reference implementation

The locator fix already exists as a working reference: `ragflow_get_article` tool patched into the local MCP bridge at `C:\Users\bohen\Documents\Hermes\ragflow-mcp\server.py` (walks chunks, exact-matches the "Article N" heading). See skill `ragflow-mcp-bridge`.

## Cloudflare quirk

Direct API calls from Python `urllib` with the default user-agent get HTTP 403 "error code: 1010" (Cloudflare browser-signature ban). Fix: send a browser User-Agent (`Mozilla/5.0 … Chrome/126 …`) and `Accept: application/json`. `curl` and `httpx` with a UA work fine.
