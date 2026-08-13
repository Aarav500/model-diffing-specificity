"""Within-cell consistency: what does the agent assert across seeds on IDENTICAL evidence?

This is the check that does not depend on adjudicating ground truth. Every seed
in a cell sees byte-identical evidence, so if the agent names mutually
incompatible objectives across seeds, at most one of them can be right --
whatever the truth about the arm. Disagreement is therefore a lower bound on
the error rate that needs no ground-truth label at all, which matters here
because every null turned out to be contaminated in some way (see ARM_NOTES.md).
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def main():
    armmap = json.loads((REPO / "results" / ".armmap.json").read_text())
    grades = {}
    for line in (REPO / "results" / "grades.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            g = json.loads(line)
            grades[g["run_id"]] = g

    cells: dict[tuple, list] = {}
    for rid, meta in armmap.items():
        g = grades.get(rid)
        if not g:
            continue
        cells.setdefault((meta["arm"], meta["prompt_variant"]), []).append(
            (meta["seed"], g["category"], g.get("asserted_objective", ""))
        )

    for key in sorted(cells):
        arm, variant = key
        rows = sorted(cells[key])
        print(f"=== {arm} / {variant} — identical evidence, {len(rows)} seeds ===")
        for seed, cat, obj in rows:
            print(f"  s{seed}: {cat:<10} {obj[:88]}")
        print()


if __name__ == "__main__":
    main()
