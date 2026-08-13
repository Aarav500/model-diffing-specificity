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
print(f"   {'field-wide framing':30s} "
      f"{'present' if 'field-wide' in txt else 'MISSING'}")
print()

# POSITIONING.md:83 BANS "cannot fail" -- Delta-Crosscoder's null is a real
# control that a broken method could fail. An earlier revision of this audit
# asserted the banned phrase, so a correct document reported MISSING. Both
# directions are now checked explicitly.
print("banned/required phrasing (POSITIONING.md:83)")
print(f"   {'BANNED cannot fail':30s} "
      f"{'PRESENT -- FIX' if 'cannot fail' in txt else 'absent (correct)'}")
print(f"   {'required zero-signal line':30s} "
      f"{'present' if 'exactly zero signal by construction' in txt else 'MISSING'}")
print()
print("must-fix 2 — registered vs exploratory separated")
print(f"   {'§8 cited':30s} {'present' if '§8' in txt else 'MISSING'}")
print(f"   {'registered test undefined':30s} "
      f"{'present' if 'undefined here' in txt else 'MISSING'}")
print(f"   {'ladder labelled exploratory':30s} "
      f"{'present' if 'exploratory' in txt else 'MISSING'}")
print(f"   {'no false pre-spec claim':30s} "
      f"{'FALSE CLAIM -- FIX' if 'both tests' in txt.lower() else 'ok'}")
print()
print("must-fix — ladder table shows all six rungs")
lad = [r.cells[0].text.strip() for r in d.tables[1].rows][1:]
print(f"   rungs in table: {lad}")
print(f"   {'six rungs':30s} {'present' if len(lad) == 6 else 'ONLY %d -- FIX' % len(lad)}")
print()
print("appendix is last (page budget)")
h1s = [p.text for p in d.paragraphs if p.style and p.style.name == "Heading 1"]
print(f"   {'appendix last':30s} "
      f"{'ok' if h1s and h1s[-1].startswith('Appendix') else 'NOT LAST -- FIX'}")
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
