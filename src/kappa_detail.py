"""Detail behind the Cohen's kappa figure: the confusion matrix and the cases
that actually carry it.

A kappa of 1.0 on a skewed distribution is easy to over-read. What earns it here
is agreement on the two NON-ASSERT cases -- a lazy grader would have called both
ASSERT -- so those are printed in full rather than summarised.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def load(p):
    out = {}
    for line in (REPO / p).read_text(encoding="utf-8").splitlines():
        if line.strip():
            g = json.loads(line)
            out[g["run_id"]] = g
    return out


def main():
    llm = load("results/grades.jsonl")
    hand = load("results/hand_grades.jsonl")
    shared = sorted(set(llm) & set(hand))

    print(f"n = {len(shared)} ({100*len(shared)/len(llm):.0f}% of {len(llm)} runs)\n")
    print("hand:", dict(Counter(hand[r]["category"] for r in shared)))
    print("llm :", dict(Counter(llm[r]["category"] for r in shared)))

    cats = ["ASSERT", "ABSTAIN", "DEGENERATE"]
    print(f"\nconfusion (rows=hand, cols=llm)")
    print(f"{'':<12}" + "".join(f"{c:>12}" for c in cats))
    for h in cats:
        row = [sum(1 for r in shared
                   if hand[r]["category"] == h and llm[r]["category"] == m)
               for m in cats]
        print(f"{h:<12}" + "".join(f"{v:>12}" for v in row))

    print("\n=== the cases that carry the agreement ===")
    for r in shared:
        if hand[r]["category"] != "ASSERT":
            print(f"\n{r}")
            print(f"  hand : {hand[r]['category']}")
            print(f"  llm  : {llm[r]['category']}  (reason={llm[r].get('reason_code')!r})")
            print(f"  hand note : {hand[r]['note'][:180]}")
            print(f"  llm  note : {str(llm[r].get('brief_justification'))[:180]}")

    disagree = [r for r in shared if hand[r]["category"] != llm[r]["category"]]
    print(f"\ndisagreements: {len(disagree)}")
    for r in disagree:
        print(f"  {r}: hand={hand[r]['category']} llm={llm[r]['category']}")


if __name__ == "__main__":
    main()
