"""D2 -- the dilution curve, with the null-arm assertion floor overlaid.

The question this answers is NOT the one ADL's sweep answers. Theirs measures
detection (grade >= 2) decaying as pretraining data is mixed in; they report
that agents fail to reach grade 2 by 1:1. This plots detection and ASSERTION
RATE on the same axes.

If assertion stays high while correctness falls, the agent does not go quiet as
the signal weakens -- it keeps naming objectives and starts naming wrong ones.
That gap is the whole point: a sensitivity-only evaluation cannot see it,
because a wrong confident answer and a correct one both look like "the agent
responded".

  python -m src.analyze_ladder
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import beta

REPO = Path(__file__).resolve().parent.parent

# Arm -> pretraining-mix ratio |D_ft| : |D_pt|. Verified against
# configs/organism/cake_bake.yaml, not inferred from adapter names.
RUNG_RATIO = {"L00": 0.0, "L01": 0.1, "L03": 0.3, "L05": 0.5, "L10": 1.0, "L20": 2.0}


def clopper_pearson(k, n, alpha=0.05):
    if n == 0:
        return (float("nan"), float("nan"))
    lo = 0.0 if k == 0 else beta.ppf(alpha / 2, k, n - k + 1)
    hi = 1.0 if k == n else beta.ppf(1 - alpha / 2, k + 1, n - k)
    return float(lo), float(hi)


def load():
    armmap = json.loads((REPO / "results" / ".armmap.json").read_text())
    grades = {}
    for line in (REPO / "results" / "grades.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            g = json.loads(line)
            grades[g["run_id"]] = g
    correct = {}
    p = REPO / "results" / "correctness.jsonl"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                c = json.loads(line)
                correct[c["run_id"]] = c
    return armmap, grades, correct


def main():
    armmap, grades, correct = load()

    rows = []
    for rid, meta in armmap.items():
        g = grades.get(rid)
        if not g:
            continue
        rows.append({**meta, "run_id": rid, "category": g["category"],
                     "detected": correct.get(rid, {}).get("detected"),
                     "grade": correct.get(rid, {}).get("grade")})

    print(f"{'rung':<6} {'ratio':>6} {'n':>4} {'assert':>8} {'detect@ASSERT':>15} "
          f"{'detect/all':>12}")
    print("-" * 60)

    pts = []
    for arm, ratio in sorted(RUNG_RATIO.items(), key=lambda kv: kv[1]):
        rs = [r for r in rows if r["arm"] == arm]
        if not rs:
            continue
        usable = [r for r in rs if r["category"] in ("ASSERT", "ABSTAIN")]
        asserts = [r for r in rs if r["category"] == "ASSERT"]
        if not usable:
            continue
        a_rate = len(asserts) / len(usable)
        det = [r for r in asserts if r["detected"]]
        # Two different denominators, both reported. detect@ASSERT is precision
        # given the agent spoke; detect/all is ADL-comparable recall.
        d_given = len(det) / len(asserts) if asserts else float("nan")
        d_all = len(det) / len(usable)
        alo, ahi = clopper_pearson(len(asserts), len(usable))
        dlo, dhi = clopper_pearson(len(det), len(usable))
        pts.append((ratio, a_rate, alo, ahi, d_all, dlo, dhi))
        print(f"{arm:<6} {ratio:>6.1f} {len(usable):>4} {a_rate:>8.2f} "
              f"{d_given:>15.2f} {d_all:>12.2f}")

    if not pts:
        raise SystemExit("No ladder arms graded yet.")

    pts.sort()
    x = [p[0] for p in pts]

    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    ax.plot(x, [p[1] for p in pts], marker="o", lw=2, color="#c0392b",
            label="asserts a specific objective")
    ax.fill_between(x, [p[2] for p in pts], [p[3] for p in pts],
                    color="#c0392b", alpha=0.15)
    ax.plot(x, [p[4] for p in pts], marker="s", lw=2, color="#2471a3",
            label="correctly identifies it (grade ≥ 2)")
    ax.fill_between(x, [p[5] for p in pts], [p[6] for p in pts],
                    color="#2471a3", alpha=0.15)

    # The gap between the two curves is the quantity a sensitivity-only
    # evaluation cannot see: confident answers that are wrong.
    ax.fill_between(x, [p[4] for p in pts], [p[1] for p in pts],
                    color="grey", alpha=0.22, label="confident but wrong")

    ax.set_xlabel("pretraining data mixed in   |D$_{ft}$| : |D$_{pt}$|")
    ax.set_ylabel("rate")
    ax.set_ylim(-0.03, 1.05)
    ax.set_title("Dilution curve: the agent keeps answering after it stops being right",
                 fontsize=12)
    ax.axvline(1.0, ls=":", color="black", lw=1)
    ax.annotate("ADL report agents fail\ngrade ≥ 2 by 1:1", xy=(1.0, 0.5),
                xytext=(1.15, 0.62), fontsize=8,
                arrowprops=dict(arrowstyle="->", lw=0.8))
    ax.legend(fontsize=9, loc="center left")
    fig.tight_layout()
    out = REPO / "results" / "figure2_dilution_curve.png"
    fig.savefig(out, dpi=200)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
