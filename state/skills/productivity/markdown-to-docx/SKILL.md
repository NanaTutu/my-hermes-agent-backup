---
name: markdown-to-docx
description: Use when converting markdown to a Word .docx without pandoc.
---

# Markdown → DOCX (pandoc-free)

Convert a markdown document into a styled Word `.docx` using the `docx` npm package — no pandoc or LibreOffice required. Ships a reusable converter (`scripts/build.js`) that parses headings, tables, bullets, numbered lists, blockquotes, and inline bold/italic/code, plus a verification script (`scripts/test.py`).

## When to use

- User says "save this as docx", "make a Word doc from this markdown", or wants a markdown deliverable in Word format.
- Host lacks pandoc (`which pandoc` is empty) or LibreOffice/soffice for rendering.

## Setup (one-time, per host)

```bash
mkdir -p ~/AppData/Local/Temp/md2docx && cd ~/AppData/Local/Temp/md2docx
npm init -y && npm install docx
# copy scripts/build.js and scripts/test.py from this skill into the dir,
# or run them directly from the skill path
```

## Convert

```bash
node build.js <input.md> <output.docx>
```

## Verify

```bash
node --check build.js                              # syntax
npm pkg set scripts.test="python test.py"          # wire once
npm test                                           # regenerates + asserts structure/content
# or directly:
python test.py <input.md> <build.js> [<output.docx>] [must_contain_substrings...]
```

## Gotchas (all hit in real runs)

- **On Windows git-bash, pass NATIVE Windows paths to `node build.js`.** MSYS paths (`/c/Users/...`) get mangled by node — it resolves them as `C:\c\Users\...` and throws `ENOENT`. Always pass `C:\Users\...` (or `C:/Users/...`) for BOTH input and output args, even when invoked from a bash shell.
- **`require('docx/package.json')` throws** `ERR_PACKAGE_PATH_NOT_EXPORTED` — the package's `exports` map blocks the subpath. Don't probe the version that way; the install either succeeded or `npm install` already errored.
- **docx-js emits `<w:t xml:space="preserve">`**, not bare `<w:t>`. When asserting on text in `word/document.xml`, count `<w:t` (with a space) — counting `<w:t>` returns 0 even though text is present.
- **Tables need dual widths.** Set `columnWidths` on the `Table` AND `width` on every `TableCell`, all in `WidthType.DXA`, summing to the table width. Content width = page width − 2×margin (A4 = 11906 DXA, 1" margin = 1440). PERCENTAGE widths break in Google Docs.
- **Shading must be `ShadingType.CLEAR`**, never `SOLID` (SOLID renders black).
- **Never use `\n`** inside a run — use separate `Paragraph` elements.
- **Bullets:** use `bullet: { level: 0 }`, never a literal `•` character.
- **Numbered lists:** docx-js cannot restart numbering across separate lists on one `numbering` reference, so render the number as a literal `"N. "` text prefix with `indent: { left: 360, hanging: 360 }` for a hanging indent. Do not use a shared `numbering` config for multiple independent lists.
- **Drop fully-empty table rows** (e.g. a `| | |` header row in a key/value metadata table) before rendering, or you get a blank shaded header row.
- **Page size:** docx-js defaults to A4. For US Letter set `page.size` explicitly (`12240 × 15840` DXA).
- **Inline parser order:** tokenize code spans first, then `**bold**`, then `*italic*` — a single regex alternation in that order prevents `*` from swallowing half of `**bold**`.

## Relationship to the bundled `docx` skill

The bundled `docx` skill (productivity) covers hand-authoring documents with docx-js and reading/editing via pandoc. This skill covers the **markdown → docx conversion path** specifically and ships a ready converter + test. Use the `docx` skill for API details and surgical XML edits; use this one to turn a markdown file into Word.
