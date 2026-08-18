#!/usr/bin/env bash
# Build the JUDGe paper and gate it.
#
# TWO pdflatex passes are mandatory, not optional tidiness: \ref resolves from
# the .aux file written by the previous run, so a single pass shipped a PDF
# reading "Figure ??" and "section ??". That is a desk-reject-grade defect that
# a source-level proofread cannot see.
#
#   bash writeup/judge2026/build.sh
set -euo pipefail
cd "$(dirname "$0")"

PY=../../.venv/Scripts/python.exe

python_check() { PYTHONIOENCODING=utf-8 "$PY" "$@"; }

echo "== figure (regenerated from study artifacts) =="
python_check figure_ladder.py

echo
echo "== latex, pass 1/2 =="
pdflatex -interaction=nonstopmode -halt-on-error paper.tex >build.log 2>&1
echo "== latex, pass 2/2 (resolves \\ref) =="
pdflatex -interaction=nonstopmode -halt-on-error paper.tex >build.log 2>&1

echo
echo "== gate =="
python_check - <<'PY'
import re, sys
from pathlib import Path

log = Path("build.log").read_text(errors="replace")
fail = 0

pages = re.search(r"Output written on paper\.pdf \((\d+) pages?", log)
n = int(pages.group(1)) if pages else -1
print(f"  pages                        {n}   (body must fit 2; refs may spill)")

# Unresolved cross-references render as '??' in the PDF.
if re.search(r"LaTeX Warning: There were undefined references", log):
    print("  undefined references         FOUND -- run again / check labels")
    fail += 1
else:
    print("  undefined references         none")

if re.search(r"LaTeX Warning: Label\(s\) may have changed", log):
    print("  labels changed               RERUN NEEDED")
    fail += 1

over = re.findall(r"Overfull \\hbox \(([\d.]+)pt", log)
bad = [o for o in over if float(o) > 5]
print(f"  overfull hboxes > 5pt        {len(bad)}")

sys.exit(fail)
PY

echo
python_check check_paper.py
echo
echo "PDF: $(pwd)/paper.pdf"
