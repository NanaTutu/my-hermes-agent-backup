# Query-routing strategy for citation-structured documents

Detects legal/code/standards references and routes each query to either the
citation index (lookup) or the semantic index (hybrid retrieval). Detection is
LAYERED: deterministic regex first (free, instant, auditable — covers ~80% of
references), LLM classification only when regex is silent.

## Reference taxonomy

| Class              | Example                                     | Detect             | Resolve                |
|--------------------|---------------------------------------------|--------------------|------------------------|
| Article            | "Article 10", "Art. 10"                     | regex              | citation idx           |
| Article + clause   | "Article 10(2)", "clause 2 of Article 10"   | regex              | citation idx + clause  |
| Section            | "Section 10"                                | regex              | citation idx           |
| Chapter            | "Chapter 3", "Chapter III", "the Citizenship chapter" | regex + roman + LLM | chapter → article range |
| Clause (bare)      | "clause 3"                                  | regex (ambiguous)  | context / fallback     |
| Range              | "Articles 5 to 12", "5–12"                  | regex              | citation idx (multi)   |
| Schedule           | "Schedule 2", "the Second Schedule"         | regex + ordinal    | citation idx           |
| Defined term       | "entrenched provision", "public office"     | LLM                | terminology idx        |
| Indirect locator   | "the Interpretation article"                | LLM                | title / semantic       |
| Cross-reference    | "the article Article 10 refers to"          | regex (chained)    | resolve 10 → read ref → resolve |
| Pure topic         | "parental citizenship"                      | (default)          | semantic               |

## Layer 1 — deterministic regex (ORDER matters)

Ranges and clause-qualified articles must be checked BEFORE bare articles, or
"Articles 5 to 12" is misread as "Article 5" and "Article 10(2)" as "Article 10".

```python
import re
RANGE   = re.compile(r"\bArt(?:icle)?s?\s+(\d+)\s*(?:to|[-–])\s*(\d+)\b", re.I)
ART_CL  = re.compile(r"\bArt(?:icle)?\.?\s+(\d+)\s*\(\s*(\d+)\s*\)", re.I)
ARTICLE = re.compile(r"\bArt(?:icle)?\.?\s+(\d+)\b", re.I)
SECTION = re.compile(r"\bSec(?:tion)?\.?\s+(\d+)\b", re.I)
CLAUSE  = re.compile(r"\bClause\.?\s*\(?\s*(\d+)\s*\)?\b", re.I)
CHAPTER = re.compile(r"\bChapter\s+(\d+|[IVXLCDM]+)\b", re.I)
SCHED   = re.compile(r"\bSchedule\s+(\d+)\b", re.I)
ORDINAL = re.compile(r"\bthe\s+(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\s+Schedule\b", re.I)
```

Each pattern emits a structured token `{type, number, clause?, confidence: 1.0}`.
"Article 10(2)" → `{type: article, number: 10, clause: 2}`.

## Layer 2 — normalize + disambiguate

- Lowercase; strip the period in "Art."/"Sec."; collapse whitespace.
- Resolve the "10" collision by TYPE: `article-10` and `section-10` are different keys.
- A bare "clause 3" resolves against a co-located citation if one exists, else → semantic.
- Deduplicate overlapping matches ("Article 10(2)" must not also emit bare "article 10").

## Layer 3 — LLM fallback (only when Layer 1 is silent)

Strict JSON extraction prompt: classify `intent="citation"` vs `"semantic"`; if
citation, emit references (type/number/clause, or `article_title` / `defined_term`).
Confidence < 1.0; threshold it (below ~0.6 → treat as semantic). Runs on a small
fraction of traffic — the probabilistic backstop, not the primary path.

## Routing decision matrix

| Detection result                    | Route                        | Confidence gate |
|-------------------------------------|------------------------------|-----------------|
| Exact citation, no other content    | LOOKUP only                  | —               |
| Citation + content words            | LOOKUP + SEMANTIC (merged)   | —               |
| Citation misses the index           | SEMANTIC (graceful; never fabricate) | —       |
| LLM says "citation"                 | LOOKUP (extracted)           | ≥ 0.6           |
| LLM says "semantic" / nothing       | HYBRID RETRIEVAL             | —               |

## Edge cases

- Plural vs singular: "Articles 5 to 12" checked before "Article 5" (ordering).
- Roman numerals ("Chapter III") and ordinals ("the Second Schedule") via maps.
- Numbers spelled out ("Article ten") — add a word→digit map only if it appears in logs, not pre-emptively.
- "does Article 10 conflict with Article 290?" → mixed: lookup both + semantic for "conflict".
- False-positive guard: "what is this article about?" (no digit) never fires; → semantic.

## Worked examples

- "What does Article 10 say?" → ARTICLE → {article,10} → no content words → LOOKUP → article-10.
- "What does Article 10(2) provide?" → ART_CL → {article,10,clause:2} → LOOKUP → surface clause 2.
- "Summarize Articles 5 to 12." → RANGE (checked first) → LOOKUP article-5…article-12.
- "What does Chapter III cover?" → CHAPTER + roman_to_int → {chapter,3} → LOOKUP chapter range.
- "What does the Interpretation article say?" → Layer 1 silent → Layer 3 → {article_title:"Interpretation"} → LOOKUP title match → article-10.
- "Which article does Article 10 refer to?" → ARTICLE {10} → LOOKUP article-10 → read its "article 9" ref → resolve article-9.
- "What does Article 999 say?" → ARTICLE {999} → index MISS → SEMANTIC fallback (returns nothing above threshold → "I don't know", never a guessed answer).
