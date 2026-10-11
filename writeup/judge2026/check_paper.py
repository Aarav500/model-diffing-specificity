"""Pre-submission gate for the JUDGe 2026 paper.

Three things a reviewer or a desk-reject can catch that a human proofread will
not reliably catch: a de-anonymising string, an overclaim the fact sheet
forbade, and a body that is over length. All three are mechanical.

  python writeup/judge2026/check_paper.py
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEX = HERE / "paper.tex"

# Strings that would break double-blind review. The repository name contains
# the author's surname, so it is as de-anonymising as the name itself.
DEANON = [
    "Aarav", "aarav", "Shah",
    "github.com/Aarav500", "model-diffing-specificity",
    r"\usepackage[final]",          # NeurIPS 'final' option prints authors
]

# Claim guards from the brief. Each is (regex, why it matters, allowed_count).
# Some words are legitimate in a negation ("not a validated detector"), so the
# check reports occurrences for eyeballing rather than failing outright -- except
# where the brief was absolute.
GUARDS = [
    (r"\bvalidated\b", "consistency must never be called validated", "review"),
    (r"\bpromising\b", "banned word", "fail"),
    (r"\bsolution\b", "banned word", "fail"),
    (r"\breinforcement learning\b|\bRL\b", "not an RL venue", "fail"),
    (r"\bproves?\b|\bdemonstrates conclusively\b", "overclaim", "review"),
]

# Hedges from the brief that MUST survive into the text.
REQUIRED = [
    (r"abandon", "the abandoned pre-registered metric must be stated"),
    (r"exploratory", "the ladder trend must be labelled exploratory in the text"),
    (r"candidate", "consistency must be called a candidate"),
    (r"reproduces|20/20", "reproduction must be stated"),
    (r"not monoton", "non-monotonicity must be disclosed"),
    # Camera-ready: the addendum's own hedges. The synthetic nulls are not
    # finetunes, the agent cannot query the models, and the second grader was
    # post hoc. Each is a place a later edit could quietly overclaim.
    # \s+ rather than a space: source lines wrap mid-phrase, and a hedge split
    # across two lines is still in the PDF.
    (r"not\s+finetunes", "synthetic nulls must be marked as not finetunes"),
    (r"cannot\s+query", "the non-interactive agent must be disclosed"),
    (r"post-hoc|post\s+hoc", "the second grader must be labelled post hoc"),
    (r"weaker\s+than\s+it\s+sounds|only\s+one\s+case", "kappa must be qualified"),
    (r"Patchscope\s+mismatch", "the Patchscope mismatch (PREREG section 14) must be disclosed"),
    (r"share\s+byte-identical\s+evidence", "seeds sharing evidence must be disclosed"),
]


def words(tex: str) -> int:
    t = re.sub(r"(?<!\\)%.*", "", tex)
    t = re.sub(r"\\(begin|end)\{[^}]*\}", " ", t)
    t = re.sub(r"\\includegraphics(\[[^\]]*\])?\{[^}]*\}", " ", t)
    t = re.sub(r"\\(label|ref|cite|texttt|emph|textbf|newblock|bibitem)\{[^}]*\}", " ", t)
    t = re.sub(r"\\[a-zA-Z]+\*?", " ", t)
    t = re.sub(r"[{}$~\\^_&]", " ", t)
    return sum(1 for w in t.split() if re.search(r"[A-Za-z0-9]", w))


def pdf_pages(pdf: Path) -> list[str] | None:
    """Every page's text via poppler's pdftotext, split on form feeds."""
    exe = shutil.which("pdftotext") or shutil.which(
        "pdftotext", path="C:/Program Files/Git/mingw64/bin;/mingw64/bin")
    if not exe:
        return None
    r = subprocess.run([exe, str(pdf), "-"], capture_output=True, text=True)
    if r.returncode != 0:
        return None
    return [p for p in r.stdout.split("\f") if p.strip()]


def clean_lines(page: str, line_numbers: bool = True) -> list[str]:
    """Page lines with the margin line numbers removed.

    The `dblblindworkshop` option numbers every line for reviewers, and
    pdftotext emits those numbers inline -- so page 3 extracts as
    "89 References", not "References". An earlier version of this check
    compared against the raw first line and reported a correctly formatted
    paper as a violation.

    The camera-ready (`final`) build has no line numbers, and stripping a
    leading number there would eat section numbers instead, hiding exactly
    the "8 What this implies" heading the spill check looks for.
    """
    out = []
    for raw in page.splitlines():
        line = raw.strip()
        if line_numbers:
            line = re.sub(r"^\d+\s*", "", line)
        if line:
            out.append(line)
    return out


def check_pages_final() -> int:
    """Camera-ready: 2 pages of body, then acknowledgments, references and an
    appendix with no page cap (JUDGe FAQ: "references and appendices do not
    count"). So the total page count is irrelevant; what matters is that no
    numbered body section starts after page 2, and that the back matter opens
    page 3 rather than body prose continuing onto it."""
    pdf = HERE / "paper.pdf"
    pages = pdf_pages(pdf) if pdf.exists() else None
    if pages is None:
        print("  paper.pdf or pdftotext missing -- page structure NOT verified")
        return 1
    print(f"  total pages                     {len(pages)}")
    back = re.compile(r"^(Acknowledg|References)")
    heading = re.compile(r"^\d+\s+[A-Z][a-z]")
    fail = 0
    if len(pages) > 2:
        lines = clean_lines(pages[2], line_numbers=False)
        if not (lines and back.match(lines[0])):
            print(f"  page 3 opens with back matter   FAIL -- opens with {lines[:1]}")
            fail = 1
        else:
            print(f"  page 3 opens with back matter   ok ({lines[0][:30]})")
        for i, page in enumerate(pages[2:], start=3):
            spilled = []
            for l in clean_lines(page, line_numbers=False):
                if back.match(l) or re.match(r"^[A-Z]\s+[A-Z][a-z]", l):
                    break       # back matter or a lettered appendix section
                if heading.match(l):
                    spilled.append(l)
            if spilled:
                print(f"  numbered section on page {i}      FAIL -- {spilled[:2]}")
                fail = 1
            if any(back.match(l) for l in clean_lines(page, line_numbers=False)):
                break
    if not fail:
        print("  body within 2 pages             ok")
    return fail


def check_pages() -> int:
    """The venue allows 2 pages of body plus unlimited references.

    Total page count alone is therefore the wrong test: 3 pages is fine when
    page 3 holds only the bibliography, and a violation when body prose spills
    onto it. This checks what is actually on the overflow page.
    """
    pdf = HERE / "paper.pdf"
    if not pdf.exists():
        print("  paper.pdf missing -- build first")
        return 1

    pages = pdf_pages(pdf)
    if pages is None:
        print("  pdftotext unavailable -- page structure NOT verified")
        print("  (check by eye: body must end on page 2)")
        return 0

    n = len(pages)
    print(f"  total pages                     {n}")
    if n <= 2:
        print("  body within 2 pages             ok")
        return 0
    if n > 3:
        print(f"  body within 2 pages             FAIL -- {n} pages")
        return 1

    lines = clean_lines(pages[2])
    opens_with_refs = bool(lines) and lines[0].lower().startswith("references")
    # A numbered section heading surviving on page 3 means body prose spilled.
    spilled = [l for l in lines if re.match(r"^\d+\s+[A-Z][a-z]", l)]
    only_refs = opens_with_refs and not spilled
    if only_refs:
        print("  page 3 is references only       ok (allowed: 2pp + refs)")
    else:
        print(f"  page 3 is references only       FAIL -- "
              f"{'does not open with References' if not opens_with_refs else spilled[:2]}")
    return 0 if only_refs else 1


CAMERA_REQUIRED = [
    "Aarav Shah", "University of Massachusetts Amherst",
    "github.com/Aarav500/model-diffing-specificity",
]
CAMERA_FORBIDDEN = ["Anonymous submission", "Under review", "4open.science"]


def is_final(src: str) -> bool:
    m = re.search(r"\\usepackage\[([^\]]*)\]\{neurips_2026\}", src)
    return bool(m and "final" in [o.strip() for o in m.group(1).split(",")])


def main() -> int:
    src = TEX.read_text(encoding="utf-8")
    fail = 0
    final = is_final(src)
    print(f"MODE  {'camera-ready (final)' if final else 'double-blind submission'}\n")

    abstract = src.split(r"\begin{abstract}")[1].split(r"\end{abstract}")[0]
    body = src.split(r"\end{abstract}")[1].split(r"\begin{thebibliography}")[0]

    aw, bw = words(abstract), words(body)
    print("LENGTH")
    print(f"  abstract {aw:>5}   target ~120       "
          f"{'ok' if 95 <= aw <= 145 else 'CHECK'}")
    # Word count was a PROXY for "fits 2 pages", used before the official
    # neurips_2026.sty was available. Now that the real style file is in the
    # repo, page structure below is the ground truth and this is advisory only
    # -- failing on it would block a paper that demonstrably fits.
    print(f"  body     {bw:>5}   (advisory; page structure is authoritative)")

    if final:
        print("\nPAGE STRUCTURE -- '2 pages body; back matter and appendix uncapped'")
        fail += check_pages_final()
    else:
        print("\nPAGE STRUCTURE -- '2 pages + references'")
        fail += check_pages()

    # Reviewers see the rendered PDF, so a string inside a LaTeX comment cannot
    # leak. Checking raw source flagged this file's own warning against
    # \usepackage[final] -- a checker that fails on its own safety note trains
    # you to ignore it. Comments are still reported, one severity down.
    rendered = re.sub(r"(?<!\\)%.*", "", src)
    comments = "\n".join(re.findall(r"(?<!\\)%.*", src))

    if final:
        # The inverse of double-blind: the byline and the real repository must
        # be there, and nothing from the review build may survive. The
        # anonymous mirror expires after the workshop, so a camera-ready that
        # still points at it would rot.
        print("\nCAMERA-READY BYLINE")
        for need in CAMERA_REQUIRED:
            ok = need in rendered
            print(f"  {need:46s} {'present' if ok else 'MISSING -- FIX'}")
            fail += 0 if ok else 1
        for bad in CAMERA_FORBIDDEN:
            hit = bad in rendered
            print(f"  {bad:46s} {'FOUND -- FIX' if hit else 'absent'}")
            fail += 1 if hit else 0
        pdf_text = "\n".join(pdf_pages(HERE / "paper.pdf") or [])
        for need in ("Aarav Shah", "Massachusetts Amherst", "Acknowledgments"):
            ok = need in pdf_text
            print(f"  in rendered PDF: {need:30s} {'yes' if ok else 'NO -- FIX'}")
            fail += 0 if ok else 1
    else:
        print("\nANONYMITY (double-blind)")
        for bad in DEANON:
            if bad in rendered:
                print(f"  {bad:34s} FOUND IN OUTPUT -- FIX")
                fail += 1
            elif bad in comments:
                print(f"  {bad:34s} in a comment only (not rendered)")
            else:
                print(f"  {bad:34s} absent")

    print("\nCLAIM GUARDS")
    for pat, why, mode in GUARDS:
        hits = re.findall(pat, src)
        if not hits:
            print(f"  {why:44s} clean")
        elif mode == "fail":
            print(f"  {why:44s} {len(hits)} FOUND -- FIX {hits[:3]}")
            fail += 1
        else:
            print(f"  {why:44s} {len(hits)} occurrence(s) -- eyeball {hits[:3]}")

    print("\nREQUIRED HEDGES (must survive)")
    for pat, why in REQUIRED:
        ok = bool(re.search(pat, src, re.I))
        print(f"  {why:52s} {'present' if ok else 'MISSING -- FIX'}")
        if not ok:
            fail += 1

    # The submission said "Ten deviations"; the camera-ready draft said "Eleven"
    # when the log had grown to thirteen. A spelled-out count goes stale every
    # time a row is added, so any count in the paper is checked against the log.
    words_to_n = {"ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
                  "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17}
    m = re.search(r"\b(\w+)\s+deviations\s+are\s+logged", rendered, re.I)
    if m and m.group(1).lower() in words_to_n or (m and m.group(1).isdigit()):
        prereg = (HERE.parent.parent / "PREREGISTRATION.md").read_text(encoding="utf-8")
        log = prereg.split("## 14. Deviations log")[1].split("\n## ")[0]
        rows = len(re.findall(r"^\| 20\d\d-", log, re.M))
        said = words_to_n.get(m.group(1).lower())
        ok = said == rows
        print(f"\nDEVIATION COUNT  paper says {m.group(1)}, log has {rows}  {'ok' if ok else 'FIX'}")
        fail += 0 if ok else 1

    # A sed lost the backslash in "0.74\linewidth", leaving "0.74inewidth".
    # LaTeX read that as the valid length 0.74in and compiled WITHOUT error,
    # silently shrinking the figure to a thumbnail and emitting stray text. A
    # clean build and a green page count both looked correct.
    print("\nMALFORMED LENGTHS (eaten backslash)")
    suspects = re.findall(r"[\d.]+(?:in|pt|em|ex|cm|mm)[a-zA-Z]+", rendered)
    print(f"  number+unit+letters              "
          f"{'clean' if not suspects else 'FOUND -- FIX ' + str(suspects)}")
    if suspects:
        fail += 1
    for cmd in ("linewidth", "textwidth", "columnwidth"):
        broken = re.findall(rf"(?<!\\){cmd}", rendered)
        if broken:
            print(f"  bare '{cmd}' without backslash   FOUND -- FIX")
            fail += 1

    # Reported, not failed: the paper is legitimately mirror-less until the
    # author creates one, and a hard failure here would train them to ignore
    # the gate. It DOES fail if a de-anonymising host got in.
    m = re.search(r"\\newcommand\{\\mirrorurl\}\{([^}]*)\}", src)
    url = m.group(1).strip() if m else None
    if final:
        print("\nCODE LINK")
        c = re.search(r"\\newcommand\{\\codeurl\}\{([^}]*)\}", src)
        curl = c.group(1).strip() if c else ""
        ok = curl.startswith("https://github.com/Aarav500/model-diffing-specificity")
        print(f"  code URL                        {curl or 'MISSING'} "
              f"{'' if ok else '-- FIX'}")
        fail += 0 if ok else 1
    else:
        print("\nANONYMOUS MIRROR")
        if m is None:
            print("  mirror macro                    MISSING from preamble -- FIX")
            fail += 1
        elif not url:
            print("  mirror URL                      not set (footnote omitted)")
            print("  -> python writeup/judge2026/set_mirror_url.py <url>")
        elif "anonymous.4open.science" not in url:
            print(f"  mirror URL                      DE-ANONYMISING HOST -- FIX: {url}")
            fail += 1
        else:
            print(f"  mirror URL                      {url}")
            rendered_has = "4open.science" in rendered
            print(f"  reaches the rendered paper      {'yes' if rendered_has else 'NO -- check \\mirrornote placement'}")
            if not rendered_has:
                fail += 1

    # Citation integrity. An uncited bibliography entry reads as padding, and a
    # cited-but-undefined key renders as [?] in the PDF. Both are cheap to catch
    # and embarrassing to ship in a paper about evaluation rigour.
    print("\nCITATIONS")
    body = src.split(r"\begin{thebibliography}")[0]
    defined = re.findall(r"\\bibitem\{([^}]+)\}", src)
    cited: set[str] = set()
    for m in re.finditer(r"\\cite[tp]?\{([^}]+)\}", body):
        cited.update(k.strip() for k in m.group(1).split(","))

    dupes = [k for k in set(defined) if defined.count(k) > 1]
    uncited = sorted(set(defined) - cited)
    undefined_keys = sorted(cited - set(defined))

    print(f"  defined {len(defined)}, cited {len(cited)}")
    print(f"  uncited entries                 {uncited or 'none'}")
    print(f"  cited but undefined             {undefined_keys or 'none'}")
    print(f"  duplicate keys                  {dupes or 'none'}")
    if undefined_keys or dupes:
        fail += 1

    # Every arXiv id in the bibliography, so provenance can be spot-checked.
    ids = re.findall(r"arXiv:(\d{4}\.\d{4,5})", src)
    print(f"  arXiv ids                       {ids}")

    print("\nFIGURE")
    for f in ("figure_ladder.pdf", "figure_ladder.png"):
        print(f"  {f:34s} {'present' if (HERE / f).exists() else 'MISSING'}")

    print(f"\n{'PASS' if fail == 0 else 'FAIL: %d problem(s)' % fail}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
