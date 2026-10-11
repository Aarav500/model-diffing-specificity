"""Second-grader agreement on the synthetic nulls -- POST HOC robustness check.

Not in Addendum A. Added after its results were seen, and logged in
PREREGISTRATION.md §14 as such. The question it answers: the authoritative
grader is gpt-5-mini, which on the second-agent runs grades its own model
family. Does a different grader, given the same frozen rubric and nothing but
the report text, code the 120 I0/R1/R2 reports the same way?

  python -m src.second_grader
"""

from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CR = REPO / "results" / "camera_ready"
SECOND = "gpt-5-2025-08-07"
OUT = CR / "grades_second_grader.jsonl"


def main():
    from src.grade import grade_one, cohens_kappa

    armmap = json.loads((CR / ".armmap.json").read_text())
    ids = sorted(r for r, m in armmap.items() if m["arm"] in ("I0", "R1", "R2"))
    done = {}
    if OUT.exists():
        done = {json.loads(l)["run_id"]: json.loads(l)
                for l in OUT.read_text(encoding="utf-8").splitlines() if l.strip()}

    lock = threading.Lock()
    with OUT.open("a", encoding="utf-8") as fh:
        def one(rid):
            rep = json.loads((CR / "reports" / f"{rid}.json").read_text(encoding="utf-8"))
            g = grade_one(rep["report"], model=SECOND)
            g["run_id"] = rid
            with lock:
                fh.write(json.dumps(g) + "\n")
                fh.flush()
                done[rid] = g

        with ThreadPoolExecutor(max_workers=8) as ex:
            list(ex.map(one, [r for r in ids if r not in done]))

    first = {json.loads(l)["run_id"]: json.loads(l)
             for l in (CR / "grades.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
    a = [first[r]["category"] for r in ids]
    b = [done[r]["category"] for r in ids]
    agree = sum(x == y for x, y in zip(a, b))
    k = cohens_kappa(a, b)
    disagreements = [(r, armmap[r], first[r]["category"], done[r]["category"])
                     for r in ids if first[r]["category"] != done[r]["category"]]
    print(f"n={len(ids)}  agreement {agree}/{len(ids)}  Cohen's kappa={k:.3f}")
    for d in disagreements:
        print("  disagree:", d)
    (CR / "second_grader_agreement.json").write_text(json.dumps({
        "second_grader": SECOND, "n": len(ids), "agree": agree, "kappa": k,
        "disagreements": disagreements, "status": "POST HOC robustness check",
    }, indent=2))


if __name__ == "__main__":
    main()
