"""Pre-submission gate for the JUDGe 2026 paper.

Three things a reviewer or a desk-reject can catch that a human proofread will
not reliably catch: a de-anonymising string, an overclaim the fact sheet
forbade, and a body that is over length. All three are mechanical.

  python writeup/judge2026/check_paper.py
"""

from __future__ import annotations

import re
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
    (r"not monotone", "non-monotonicity must be disclosed"),
    (r"weaker than it sounds|only one case", "kappa must be qualified"),
]


def words(tex: str) -> int:
    t = re.sub(r"(?<!\\)%.*", "", tex)
    t = re.sub(r"\\(begin|end)\{[^}]*\}", " ", t)
    t = re.sub(r"\\includegraphics(\[[^\]]*\])?\{[^}]*\}", " ", t)
    t = re.sub(r"\\(label|ref|cite|texttt|emph|textbf|newblock|bibitem)\{[^}]*\}", " ", t)
    t = re.sub(r"\\[a-zA-Z]+\*?", " ", t)
    t = re.sub(r"[{}$~\\^_&]", " ", t)
    return sum(1 for w in t.split() if re.search(r"[A-Za-z0-9]", w))


def main() -> int:
    src = TEX.read_text(encoding="utf-8")
    fail = 0

    abstract = src.split(r"\begin{abstract}")[1].split(r"\end{abstract}")[0]
    body = src.split(r"\end{abstract}")[1].split(r"\begin{thebibliography}")[0]

    aw, bw = words(abstract), words(body)
    print("LENGTH")
    print(f"  abstract {aw:>5}   target ~120       "
          f"{'ok' if 95 <= aw <= 145 else 'CHECK'}")
    print(f"  body     {bw:>5}   target 1100-1400  "
          f"{'ok' if 1100 <= bw <= 1400 else 'CHECK'}")
    if not (1100 <= bw <= 1400):
        fail += 1

    # Reviewers see the rendered PDF, so a string inside a LaTeX comment cannot
    # leak. Checking raw source flagged this file's own warning against
    # \usepackage[final] -- a checker that fails on its own safety note trains
    # you to ignore it. Comments are still reported, one severity down.
    rendered = re.sub(r"(?<!\\)%.*", "", src)
    comments = "\n".join(re.findall(r"(?<!\\)%.*", src))

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

    print("\nFIGURE")
    for f in ("figure_ladder.pdf", "figure_ladder.png"):
        print(f"  {f:34s} {'present' if (HERE / f).exists() else 'MISSING'}")

    print(f"\n{'PASS' if fail == 0 else 'FAIL: %d problem(s)' % fail}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
