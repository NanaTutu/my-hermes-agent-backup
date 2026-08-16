---
name: rag-retrieval-diagnosis
description: Use when debugging RAG retrieval failures and query routing.
---

# RAG Retrieval Diagnosis

Systematic diagnosis of why a RAG system retrieves the wrong (or no) chunks, and the fixes. Applies to any engine (RAGFlow, LangChain, LlamaIndex, custom). The most common — and most misdiagnosed — case is structured documents with numbered units (constitutions, contracts, legislation) where users ask "What does Article N say?".

## Step 0 — classify the failure before touching anything

Three problems live at three boundaries; each has exactly one isolation test:

1. **Retrieval failure** — the correct chunk never enters the candidate set.
   Test: run retrieval ALONE (no LLM). Is the target chunk in top-N? `No` → this is it.
   Fix lives in the retriever (indexing, chunking, embeddings, weights, query rewriting, routing, filters).

2. **Context-assembly failure** — the chunk IS retrieved but doesn't reach the prompt intact (truncation, token-budget cut, wrong field extracted, chunk dedup'd away, metadata stripped so the LLM can't identify it).
   Test: log the exact prompt. Is the chunk's full text + metadata actually present? `No` → this.
   Fix lives in the prompt-building code between retriever and model.

3. **Generation failure** — the content is in the prompt but the model still answers wrong (over-cautious "I don't know", hallucination, contradicts the retrieved text, weak model, bad system prompt).
   Test: bypass retrieval and paste the chunk directly into a fresh chat. Model still wrong → this.
   Fix lives in the model + system prompt.

Run the three tests in order and stop at the first "No". Most "the LLM says I don't know" reports are actually Problem 1, and people wrongly tune the model or prompt. This taxonomy is the single highest-value mental model in RAG debugging.

## The core distinction: locator vs semantic queries

Two query types must not share one path:

- **Semantic** ("what rights do accused persons have") → similarity retrieval (vector + full-text hybrid). Weights matter here.
- **Locator / reference** ("Article 10", "Section 5", "Clause 3") → exact lookup on an identifier. Similarity is the wrong tool.

Why locator queries defeat similarity retrieval (the "Article 10" problem):

- The identifier's only unique part is a NUMBER, which has ~no semantic signal. An embedding places "10" next to 9 / 11 / 100 ("a number"), not "the chunk labeled 10".
- Full-text (BM25) is bag-of-words: it throws away the adjacency that makes "Article 10" unique. "article" appears in every chunk (IDF ≈ 0); "10" collides with "10 days", "10 per cent", "Section 10", and "Article 100" as substring. Term score comes out flat and non-discriminative.
- Result: the correct chunk has a retrieval signature nearly identical to its siblings. It is not "missed" — it is *indistinguishable*.

Crucial: **weights cannot fix this.** Even full-text = 1.0 fails (verified empirically). Zero signal × any weight = zero.

## Two indexes: navigation vs search

A structured document has two access paths; RAG frameworks ship only the second:

- **Navigate / lookup** — "go to Article 10". Exact, deterministic, driven by the document's own numbering. Implemented as a **citation index**: identifier → chunk, a key-value table built at INGESTION time. This is pointer resolution — a compiler's symbol table, an IDE's "go to definition", Westlaw resolving a citation.
- **Search / similarity** — "find text about citizenship". Probabilistic, driven by meaning. This is the semantic index (vector + full-text).

The failure is a **ghost identifier**: a citation ("Article 10") has no first-class home in any of the engine's three identity levels — document (a whole file), chunk (an opaque hash), metadata (usually a document-level array). It exists only as human-readable prose, not a queryable key. Fix: promote it to a resolvable key at ingestion, and route locator queries to it.

A legal document carries several overlapping structures, each warranting its own index rather than one flat chunk index: hierarchy (article→clause) → citation index; cross-references ("subject to article 9") → link/graph index; definitions ("entrenched provision") → terminology index; doctrine → semantic index; amendments → version layer. Engines that extract structure at parse time often STORE it as inert document metadata and never turn it into a navigable index — structure captured, then discarded.

## Index vs context: which fields earn an index entry

Two independent tests per field: (1) does its value change WHICH chunk you fetch → index it; (2) does the LLM answer better seeing it → pass as context. A field can be either, both, or neither.

Match the index mode to the data type:

- **Vector** — MEANING only (chunk content). Never embed identifiers: a number has no semantic direction and adds noise.
- **Full-text** — exact TERMINOLOGY (titles, defined terms, load-bearing phrases).
- **Exact-match / filter** — IDENTIFIERS and SCOPE (unit_number, unit_type, chapter). Identifiers go here, never to vector nor to free full-text (bag-of-words destroys "Article 10"'s adjacency).

Derived lookup keys (`article-10`) are index-only, never context — the model doesn't need to see them. Pass everything else useful (unit_number, title, chapter, document name) as context so the LLM can cite precisely; it costs a few tokens and is the difference between "the constitution says X" and "Article 10 (Interpretation), Chapter III — Citizenship, says X".

## Diagnosis procedure (graded retrieval test suite)

1. Build a graded query list tagged by intent class, each with a gold-standard target (the expected unit number / chunk id):
   - exact-identifier: "What does Article 10 say?", "Tell me about Article 1."
   - title: "What is the title of Article 10?"
   - semantic: a paraphrase of the article's actual content
   - clause: "What does Article 10(2) provide?"
   - cross-reference: "Which article does Article 10 refer to?"
2. Run retrieval only (no LLM). Record top-N (N=8), the rank of the target, and split vector vs term similarity per hit.
3. PASS = target in top-N. The pass/fail *pattern across classes* isolates the fault:
   - semantic passes, locator misses → build a locator path (below). This is the classic result.
   - everything misses → indexing / embedding problem.
   - everything passes but the app still fails → it's context-assembly or generation (Step 0).
4. Re-run the suite as the regression harness after every change.
A runnable, parameterized suite: `scripts/retrieval_test_suite.py`.

## Fixes by mode

- **Locator path (required for "Article N")**: a query router in the app layer. Regex for "Article / Art. / Section / Clause N" → resolve to the exact chunk via the engine's chunk API or a metadata filter → hand that chunk to the LLM. This is the ONLY thing that resolves numbered identifiers; no amount of tuning the similarity path does it. A bare regex is the minimum; the robust form is a layered detector (deterministic regex first, LLM fallback for indirect references like "the Interpretation article") — see `references/query-routing-strategy.md` for the full reference taxonomy, grammar, decision matrix, and worked examples.
- **Semantic path**: for legal/technical docs, bias full-text (0.2/0.8 to 0.1/0.9) because exact wording is load-bearing ("may" vs "shall", defined terms, cross-references); accept the paraphrase-recall cost. Don't over-tune — the gap from 0.7 to 0.9 is marginal.
- **Data hygiene (helps, but is NOT sufficient for locators)**: Markdown headings (`## Article N` / `### Title`) so the chunker splits deterministically; one unit = one parent chunk (use parent-child chunking for long units); attach per-chunk metadata (unit_type / unit_number / unit_title / chapter) for filtering, citation, and reranking. Enriching a chunk improves GENERATION and FILTERABILITY — it does not improve similarity ranking.

## Pitfalls

- Tuning top-K, similarity threshold, or adding a reranker for a locator failure is noise — the signal isn't there.
- Metadata attached at DOCUMENT level (one big array of all unit numbers) is useless for article precision: engines that filter by metadata usually filter FILES, not chunks. Verify granularity empirically before relying on a metadata filter.
- A number is the hardest thing to retrieve. Structurally-explicit ≠ retrievable.
- A trailing `\b` after an optional clause-capture group silently drops the clause: in `...(\d+)(?:\s*\(\s*(\d+)\s*\))?\b`, `\b` cannot match after `)` (a non-word char followed by a space), so the regex backtracks and reads "Article 10(2)" as "Article 10". Drop the trailing `\b`, or use a separate clause-aware pattern checked before the bare-article pattern. Verify clause capture against the test matrix, not by eye — this shipped as a silent bug and the matrix caught it.
- The locator fix works on UN-restructured data. A regex router + a citation index keyed on the heading text already present in chunks ("Article N" as a standalone line) flips identifier MISS→HIT with no metadata and no Markdown restructure. Caveat: the heading is often NOT the first line — a parent chapter heading gets prepended, so match with multiline `^Article\s+(\d+)$`, not `content.split("\n")[0]`. Restructure + per-chunk metadata are hygiene and scale optimization, NOT prerequisites for fixing "Article N".
- If a hosted engine's API 403s with "error code: 1010", it's Cloudflare rejecting a default Python urllib user-agent — set a browser UA (see the reference file).

## References

- `references/ragflow-empirical-findings.md` — RAGFlow-specific mechanics (metadata_condition schema, file-level filtering proof, chunking, weight formula) and a worked test result.
- `references/query-routing-strategy.md` — full layered query-routing design: reference taxonomy, ordered regex grammar, normalization, LLM-fallback prompt, routing decision matrix, edge cases, and worked examples.
