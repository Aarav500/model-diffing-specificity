"""Ladder statistics — the PRE-REGISTERED test and the exploratory one, separated.

This file exists because the p-values were previously computed in an ad-hoc shell
one-liner and never committed. A number in a write-up with no code path in the
repo is not reproducible, and this repo is meant to be handed to an agent.

PREREGISTRATION.md §8 registers exactly one ladder test:

    "Ladder: logistic regression of ASSERT on log dilution fraction"

Running it is the honest thing to do, and the result is itself a finding: ASSERT
is 1.00 on all six rungs, so the outcome is CONSTANT and the regression is
degenerate — there is no variance to model. That is the same failure the project
was built around: a metric that is undefined on constant input, reported as
though it had produced a number.

The trend actually reported in the write-up (grade >= 4 against mixing ratio) is
a DIFFERENT test on a different outcome, and §8's multiplicity rule requires it
be labelled exploratory. It is labelled exploratory here and in the document.

  python -m src.ladder_stats
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from scipy.stats import fisher_exact, spearmanr

REPO = Path(__file__).resolve().parent.parent
RUNG_RATIO = {"L00": 0.0, "L01": 0.1, "L03": 0.3, "L05": 0.5, "L10": 1.0, "L20": 2.0}


def load():
    armmap = json.loads((REPO / "results" / ".armmap.json").read_text())
    grades = {}
    for line in (REPO / "results" / "grades.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            g = json.loads(line)
            grades[g["run_id"]] = g
    correct = {}
    for line in (REPO / "results" / "correctness.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            c = json.loads(line)
            correct[c["run_id"]] = c
    rows = []
    for rid, meta in armmap.items():
        if meta["arm"] not in RUNG_RATIO:
            continue
        g = grades.get(rid)
        if not g:
            continue
        rows.append({**meta, "category": g["category"],
                     "grade": correct.get(rid, {}).get("grade")})
    return rows


def main():
    rows = load()

    print("=" * 68)
    print("PRE-REGISTERED (PREREGISTRATION.md §8)")
    print("  logistic regression of ASSERT on log dilution fraction")
    print("=" * 68)
    y, x = [], []
    for r in rows:
        if r["category"] not in ("ASSERT", "ABSTAIN"):
            continue
        ratio = RUNG_RATIO[r["arm"]]
        # log(0) is undefined; §8 did not specify an offset. log1p is the
        # least-arbitrary choice and is stated rather than silently applied.
        x.append(math.log1p(ratio))
        y.append(1 if r["category"] == "ASSERT" else 0)
    y = np.array(y)
    print(f"  n = {len(y)}   ASSERT = {int(y.sum())}   ABSTAIN = {int((1-y).sum())}")
    if y.min() == y.max():
        print("  OUTCOME IS CONSTANT (ASSERT on every run).")
        print("  Logistic regression is DEGENERATE: perfect separation with no")
        print("  variance to model, so no coefficient or p-value is estimable.")
        print("  REPORTED RESULT: the registered test is undefined on this data.")
        print("  This is not a null result -- it is the metric failing to be")
        print("  computable, which is the failure mode this project is about.")
    else:
        import statsmodels.api as sm
        m = sm.Logit(y, sm.add_constant(np.array(x))).fit(disp=0)
        print(m.summary())

    print()
    print("=" * 68)
    print("EXPLORATORY (not pre-registered; §8 multiplicity rule applies)")
    print("  grade >= 4 against mixing ratio")
    print("=" * 68)
    ratios, rates, ks = [], [], []
    for arm, ratio in sorted(RUNG_RATIO.items(), key=lambda kv: kv[1]):
        rs = [r for r in rows if r["arm"] == arm]
        usable = [r for r in rs if r["category"] in ("ASSERT", "ABSTAIN")]
        strict = [r for r in usable if (r["grade"] or 0) >= 4]
        ratios.append(ratio)
        rates.append(len(strict) / len(usable))
        ks.append((len(strict), len(usable)))
        print(f"  {arm}  ratio={ratio:<4} grade>=4 {len(strict):>2}/{len(usable):<3} "
              f"= {rates[-1]:.2f}")

    rho, p_rho = spearmanr(ratios, rates)
    print(f"\n  Spearman rho = {rho:.3f}, p = {p_rho:.4f}   [EXPLORATORY]")
    odds, p_f = fisher_exact([[ks[0][0], ks[0][1] - ks[0][0]],
                              [ks[-1][0], ks[-1][1] - ks[-1][0]]])
    print(f"  unmixed vs 1:2, Fisher exact p = {p_f:.5f}, odds = {odds:.2f}   [EXPLORATORY]")

    print()
    print("=" * 68)
    print("DIFF NORM vs ACCURACY -- scope check")
    print("=" * 68)
    norms = {}
    for arm in list(RUNG_RATIO) + ["P", "N0", "N1", "N2"]:
        p = REPO / "results" / "artifacts" / arm / "artifacts.json"
        if p.exists():
            a = json.loads(p.read_text(encoding="utf-8"))
            vals = [v for vs in a["diff_norms_by_layer_position"].values() for v in vs]
            norms[arm] = sum(vals) / len(vals)
    lad_n = [norms[a] for a, _ in sorted(RUNG_RATIO.items(), key=lambda kv: kv[1])]
    r2, p2 = spearmanr(lad_n, rates)
    print(f"  within the mix1 family: Spearman rho = {r2:.2f}, p = {p2:.3f}   [EXPLORATORY]")
    print(f"  ladder norms: {[round(v) for v in lad_n]}  (NOT monotone -- falls at the first step)")
    print(f"  ACROSS arms the relation REVERSES: P norm {norms['P']:.0f} has the best accuracy, "
          f"N0 norm {norms['N0']:.0f} has no narrow objective at all.")
    print("  => the claim holds only WITHIN a matched family. Scoped accordingly.")


if __name__ == "__main__":
    main()
