"""End-to-end test for scripts/build.js (markdown -> docx converter).

Usage:
    python test.py <input.md> <build.js> [<output.docx>] [must_contain_substrings...]

Regenerates the .docx through the real converter and asserts the output is a
structurally valid OOXML package containing the expected content. Exits non-zero
on any failure.
"""
import os
import subprocess
import sys
import tempfile
import zipfile

if len(sys.argv) < 3:
    print("usage: python test.py <input.md> <build.js> [<output.docx>] [must_contain...]")
    sys.exit(2)

src = sys.argv[1]
build = sys.argv[2]
out = sys.argv[3] if len(sys.argv) > 3 else os.path.join(tempfile.gettempdir(), "md2docx_test_output.docx")
must_contain = sys.argv[4:]

# 1. regenerate through the real converter
r = subprocess.run(["node", build, src, out], capture_output=True, text=True)
if r.returncode != 0:
    print("FAIL: converter errored\n" + r.stderr)
    sys.exit(1)
if not os.path.exists(out):
    print("FAIL: output file not written")
    sys.exit(1)

# 2. structural validation
z = zipfile.ZipFile(out)
names = z.namelist()
for req in ("word/document.xml", "word/styles.xml", "[Content_Types].xml"):
    if req not in names:
        print(f"FAIL: missing part {req}")
        sys.exit(1)

d = z.read("word/document.xml").decode("utf-8")

# 3. content assertions (note: docx-js writes <w:t xml:space="preserve">, so count "<w:t" with a space)
checks = {
    "text runs present": d.count("<w:t") > 100,
    "heading styles present": 'w:val="Heading' in d,
}
failed = [k for k, ok in checks.items() if not ok]
for s in must_contain:
    if s not in d:
        failed.append(f"missing substring: {s!r}")

if failed:
    print("FAIL: " + "; ".join(failed))
    sys.exit(1)

n_tables = d.count("<w:tbl>")
extra = f", {len(must_contain)} substring(s) matched" if must_contain else ""
print(f"PASS: valid OOXML, {n_tables} table(s), headings + text present{extra}")
