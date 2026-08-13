"""Grade DISTRIBUTION down the ladder, not just the >= 2 binary.

Motivation: detect@>=2 came out at 1.00 on every rung, which appears to
contradict ADL's report that agents fail grade >= 2 by a 1:1 mixture. Before
claiming any such contradiction, look at where the mass actually sits. A binary
threshold can hide a large, monotone degradation happening entirely above it.

The likely reconciliation is that ADL's SDF rubric grades % of KEY FACTS
recovered, whereas the rubric I reconstructed grades domain identification at
level 2 (I do not have their rubric text). If so, both can be true: dilution
destroys recoverable specifics while leaving the domain plainly readable.
"""

from __future__ import annotations

import json
import statistics
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RUNG_RATIO = {"L00": 0.0, "L01": 0.1, "L03": 0.3, "L05": 0.5, "L10": 1.0, "L20": 2.0}


def main():
    armmap = json.loads((REPO / "results" / ".armmap.json").read_text())
    correct = {}
    for line in (REPO / "results" / "correctness.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            c = json.loads(line)
            correct[c["run_id"]] = c

    print(f"{'rung':<6} {'ratio':>6} {'n':>4} {'mean':>6} {'median':>7}   distribution")
    print("-" * 66)
    for arm, ratio in sorted(RUNG_RATIO.items(), key=lambda kv: kv[1]):
        gs = [correct[r]["grade"] for r, m in armmap.items()
              if m["arm"] == arm and r in correct and correct[r].get("grade")]
        if not gs:
            continue
        dist = dict(sorted(Counter(gs).items()))
        bar = "".join(f" {k}:{v:<3}" for k, v in dist.items())
        print(f"{arm:<6} {ratio:>6.1f} {len(gs):>4} {statistics.mean(gs):>6.2f} "
              f"{statistics.median(gs):>7.1f}  {bar}")

    # Arm P for reference (different organism family: hcasademunt, not stewy33)
    gs = [correct[r]["grade"] for r, m in armmap.items()
          if m["arm"] == "P" and r in correct and correct[r].get("grade")]
    if gs:
        dist = dict(sorted(Counter(gs).items()))
        bar = "".join(f" {k}:{v:<3}" for k, v in dist.items())
        print(f"\n{'P':<6} {'--':>6} {len(gs):>4} {statistics.mean(gs):>6.2f} "
              f"{statistics.median(gs):>7.1f}  {bar}   (different organism family)")


if __name__ == "__main__":
    main()
