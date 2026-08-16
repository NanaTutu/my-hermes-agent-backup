// markdown -> docx converter (no pandoc). Usage: node build.js <input.md> <output.docx>
const fs = require('fs');
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell,
  WidthType, BorderStyle, ShadingType,
} = require('docx');

const SRC = process.argv[2];
const OUT = process.argv[3];
if (!SRC || !OUT) { console.error('usage: node build.js <input.md> <output.docx>'); process.exit(1); }
const md = fs.readFileSync(SRC, 'utf8');

const A4W = 11906, A4H = 16838;   // DXA; swap to 12240x15840 for US Letter
const MARGIN = 1440;              // 1 inch
const CONTENT_W = A4W - MARGIN * 2;

// inline formatting parser (code spans first, then **bold**, then *italic*)
function inline(text, base = {}) {
  const runs = [];
  const re = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)/g;
  let last = 0, m;
  const parts = [];
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) parts.push({ t: text.slice(last, m.index), type: 'plain' });
    const tok = m[0];
    if (tok.startsWith('`')) parts.push({ t: tok.slice(1, -1), type: 'code' });
    else if (tok.startsWith('**')) parts.push({ t: tok.slice(2, -2), type: 'bold' });
    else parts.push({ t: tok.slice(1, -1), type: 'italic' });
    last = m.index + tok.length;
  }
  if (last < text.length) parts.push({ t: text.slice(last), type: 'plain' });

  for (const p of parts) {
    const opt = { text: p.t, ...base };
    if (p.type === 'bold') opt.bold = true;
    if (p.type === 'italic') opt.italics = true;
    if (p.type === 'code') { opt.font = 'Consolas'; opt.size = (base.size || 22) - 2; opt.color = base.color || '1F3864'; }
    runs.push(new TextRun(opt));
  }
  return runs;
}

function colWidths(n) {
  if (n === 2) { const a = Math.floor(CONTENT_W * 0.32); return [a, CONTENT_W - a]; }
  const w = Math.floor(CONTENT_W / n);
  const widths = new Array(n).fill(w);
  widths[n - 1] = CONTENT_W - w * (n - 1);
  return widths;
}

function makeTable(rows) {
  const widths = colWidths(rows[0].length);
  const tableRows = rows.map((cells, ri) => {
    const isHeader = ri === 0;
    return new TableRow({
      children: cells.map((cell, ci) =>
        new TableCell({
          width: { size: widths[ci], type: WidthType.DXA },
          shading: isHeader ? { type: ShadingType.CLEAR, fill: 'E8EAF0', color: 'auto' } : undefined,
          margins: { top: 80, bottom: 80, left: 120, right: 120 },
          children: [new Paragraph({ spacing: { after: 0 }, children: inline(cell, isHeader ? { bold: true } : {}) })],
        })
      ),
    });
  });
  return new Table({
    columnWidths: widths,
    width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA },
    rows: tableRows,
  });
}

function render(b) {
  switch (b.type) {
    case 'h1': return new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { after: 120 }, children: inline(b.text) });
    case 'h2': return new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 260, after: 120 }, children: inline(b.text) });
    case 'h3': return new Paragraph({ heading: HeadingLevel.HEADING_3, spacing: { before: 200, after: 100 }, children: inline(b.text) });
    case 'para': return new Paragraph({ spacing: { after: 120 }, children: inline(b.text) });
    case 'bullet': return new Paragraph({ bullet: { level: 0 }, spacing: { after: 60 }, children: inline(b.text) });
    case 'num': return new Paragraph({ indent: { left: 360, hanging: 360 }, spacing: { after: 80 }, children: inline(b.text) });
    case 'quote':
      return new Paragraph({
        indent: { left: 360 },
        border: { left: { style: BorderStyle.SINGLE, size: 12, color: 'C9A227', space: 8 } },
        spacing: { before: 120, after: 120 },
        children: inline(b.text, { italics: true }),
      });
    case 'table': return makeTable(b.rows);
  }
  return new Paragraph({ children: [] });
}

// block parser
const lines = md.split(/\r?\n/);
const blocks = [];
let i = 0;
while (i < lines.length) {
  const line = lines[i];
  if (line.trim().startsWith('|')) {
    const tableLines = [];
    while (i < lines.length && lines[i].trim().startsWith('|')) { tableLines.push(lines[i].trim()); i++; }
    let rows = [];
    for (const tl of tableLines) {
      if (/^\|[\s:|-]+\|$/.test(tl)) continue; // header separator row
      rows.push(tl.slice(1, -1).split('|').map((c) => c.trim()));
    }
    rows = rows.filter((r) => !r.every((c) => c === '')); // drop fully-empty rows
    if (rows.length) blocks.push({ type: 'table', rows });
    continue;
  }
  if (/^---+\s*$/.test(line.trim())) { i++; continue; } // horizontal rule
  if (/^###\s+/.test(line)) { blocks.push({ type: 'h3', text: line.replace(/^###\s+/, '') }); i++; continue; }
  if (/^##\s+/.test(line)) { blocks.push({ type: 'h2', text: line.replace(/^##\s+/, '') }); i++; continue; }
  if (/^#\s+/.test(line)) { blocks.push({ type: 'h1', text: line.replace(/^#\s+/, '') }); i++; continue; }
  if (/^>\s?/.test(line)) { blocks.push({ type: 'quote', text: line.replace(/^>\s?/, '') }); i++; continue; }
  if (/^\s*[-*]\s+/.test(line)) { blocks.push({ type: 'bullet', text: line.replace(/^\s*[-*]\s+/, '') }); i++; continue; }
  const nm = line.match(/^\s*(\d+\.\s+)(.*)$/);
  if (nm) { blocks.push({ type: 'num', text: nm[1] + nm[2] }); i++; continue; }
  if (line.trim() === '') { i++; continue; }
  blocks.push({ type: 'para', text: line.trim() });
  i++;
}

const children = [];
for (const b of blocks) {
  children.push(render(b));
  if (b.type === 'table') children.push(new Paragraph({ spacing: { after: 60 }, children: [new TextRun({ text: '' })] }));
}

const doc = new Document({
  styles: { default: { document: { run: { font: 'Calibri', size: 22 } } } },
  sections: [{
    properties: { page: { size: { width: A4W, height: A4H }, margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN } } },
    children,
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(OUT, buf);
  console.log('WROTE ' + OUT + ' (' + buf.length + ' bytes)');
}).catch((e) => { console.error(e); process.exit(1); });
