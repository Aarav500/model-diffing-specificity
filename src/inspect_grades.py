"""Audit the graded runs per arm: claim_scope, confidence, and what was asserted.

A false-positive rate is only as trustworthy as the classification behind it.
This prints the raw material so the headline number can be checked rather than
believed -- in particular whether N2's assertions are scoped as `difference`
(a genuine false positive) or `shared` (correct, and recounted as ABSTAIN by
PREREGISTRATION.md §4).
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def main():
    armmap = json.loads((REPO / "results" / ".armmap.json").read_text())
    grades = {}
    for line in (REPO / "results" / "grades.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            g = json.loads(line)
            grades[g["run_id"]] = g

    for arm in ["P", "N1", "N2", "N0"]:
        rows = [(r, g) for r, g in grades.items()
                if armmap.get(r, {}).get("arm") == arm]
        print(f"=== {arm}   n={len(rows)} ===")
        print("  category   :", dict(Counter(g["category"] for _, g in rows)))
        print("  claim_scope:", dict(Counter(g["claim_scope"] for _, g in rows)))
        print("  confidence :", dict(Counter(g["confidence"] for _, g in rows)))
        by_prompt = Counter((armmap[r]["prompt_variant"], g["category"]) for r, g in rows)
        print("  by prompt  :", dict(by_prompt))
        objs = [g["asserted_objective"] for _, g in rows if g.get("asserted_objective")]
        print(f"  asserted ({len(objs)}):")
        for o in objs[:8]:
            print("    -", o[:100])
        print()


if __name__ == "__main__":
    main()
