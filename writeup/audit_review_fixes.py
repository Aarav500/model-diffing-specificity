"""Verify the reviewer's must-fix items landed, and re-count the word budget."""

from pathlib import Path
import docx

REPO = Path(__file__).resolve().parent.parent
d = docx.Document(str(REPO / "writeup" / "MATS_Nanda_Application_ModelDiffingFPR.docx"))

on, prose = False, 0
for p in d.paragraphs:
    t = p.text.strip()
    if t == "Executive summary":
        on = True
        continue
    if t.startswith("— end of executive summary"):
        break
    if on:
        prose += len(t.split())

# The reviewer counts the ladder table separately; report both.
tbl_words = 0
for tb in d.tables[1:]:
    for r in tb.rows:
        for c in r.cells:
            tbl_words += len(c.text.split())

txt = "\n".join(p.text for p in d.paragraphs)
for tb in d.tables:
    for r in tb.rows:
        txt += "\n" + " | ".join(c.text for c in r.cells)

print(f"exec summary prose : {prose}/600  {'OK' if prose <= 600 else 'OVER by %d' % (prose-600)}")
print(f"  + ladder table   : {prose + tbl_words} inclusive")
print()
print("must-fix 1 — the four papers")
for paper in ["Delta-Crosscoder", "AuditBench", "Model Organisms Are Leaky",
              "Cross-Architecture Diffing"]:
    print(f"   {paper:30s} {'present' if paper in txt else 'MISSING'}")
print(f"   {'the quotable line':30s} "
      f"{'present' if 'a control that cannot fail' in txt else 'MISSING'}")
print(f"   {'field-wide framing':30s} "
      f"{'present' if 'field-wide' in txt else 'MISSING'}")
print()
print("must-fix 2 — pre-registration cited")
print(f"   {'PREREGISTRATION.md §8':30s} "
      f"{'present' if 'PREREGISTRATION.md §8' in txt else 'MISSING'}")
print()
print("judgment 4 — section order")
for h in [p.text for p in d.paragraphs if p.style and p.style.name == "Heading 1"]:
    print("  ", h)
print()
print("unchanged framing (must NOT be smoothed)")
for phrase in ["failed to measure a false-positive rate",
               "every null I built contained a real signal",
               "What replaced it is sharper"]:
    print(f"   {'present' if phrase in txt else 'LOST'}  {phrase}")
