"""JUDGe 2026 Figure 1 -- the dilution ladder.

The one figure in the paper. It has to carry the whole claim: assertion is flat
while accuracy collapses, so the vertical gap between the two series IS the
finding -- it is what a sensitivity-only evaluation cannot see.

Numbers are read from the study artifacts, never typed, so the figure cannot
drift from the table. Run:

  python writeup/judge2026/figure_ladder.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import beta

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

from src.ladder_stats import RUNG_RATIO, load  # noqa: E402

OUT = Path(__file__).resolve().parent

# Ordinal spacing, not linear. The rungs are 0, 0.1, 0.3, 0.5, 1.0, 2.0 -- a
# linear x-axis would crush the first four against the origin and a log axis is
# undefined at 0. Equal spacing makes no claim about the spacing of the ratios.
LABELS = {0.0: "1:0", 0.1: "1:0.1", 0.3: "1:0.3",
          0.5: "1:0.5", 1.0: "1:1", 2.0: "1:2"}

ASSERT_C = "#B42318"   # assertion rate -- the flat line
ACC_C = "#1D4ED8"      # grade >= 4 accuracy -- the collapsing line
GAP_C = "#94A3B8"


def clopper_pearson(k: int, n: int, alpha: float = 0.05):
    """Exact binomial interval; matches the intervals used elsewhere in the study."""
    lo = 0.0 if k == 0 else beta.ppf(alpha / 2, k, n - k + 1)
    hi = 1.0 if k == n else beta.ppf(1 - alpha / 2, k + 1, n - k)
    return lo, hi


def main() -> int:
    rows = load()
    ratios = sorted(RUNG_RATIO.values())
    arm_of = {v: k for k, v in RUNG_RATIO.items()}

    x = np.arange(len(ratios))
    a_rate, a_lo, a_hi = [], [], []
    g_rate, g_lo, g_hi = [], [], []
    ns = []

    for r in ratios:
        rs = [q for q in rows if q["arm"] == arm_of[r]]
        usable = [q for q in rs if q["category"] in ("ASSERT", "ABSTAIN")]
        n = len(usable)
        ka = sum(1 for q in usable if q["category"] == "ASSERT")
        kg = sum(1 for q in usable if (q["grade"] or 0) >= 4)
        ns.append(n)
        for k, rate, lo, hi in ((ka, a_rate, a_lo, a_hi), (kg, g_rate, g_lo, g_hi)):
            l, h = clopper_pearson(k, n)
            rate.append(k / n)
            lo.append(l)
            hi.append(h)

    a_rate, g_rate = np.array(a_rate), np.array(g_rate)

    fig, ax = plt.subplots(figsize=(6.2, 1.95), dpi=300)

    # The gap is the finding, so it is drawn first and labelled in the legend
    # rather than left as incidental whitespace between two lines.
    ax.fill_between(x, g_rate, a_rate, color=GAP_C, alpha=0.28, linewidth=0,
                    label="Gap: invisible to a sensitivity-only evaluation")

    ax.errorbar(x, a_rate, yerr=[a_rate - np.array(a_lo), np.array(a_hi) - a_rate],
                color=ASSERT_C, marker="o", markersize=5, linewidth=1.9,
                capsize=2.5, elinewidth=0.9, label="Assertion rate", zorder=3)
    ax.errorbar(x, g_rate, yerr=[g_rate - np.array(g_lo), np.array(g_hi) - g_rate],
                color=ACC_C, marker="s", markersize=4.5, linewidth=1.9,
                linestyle="--", markerfacecolor="white", markeredgewidth=1.4,
                capsize=2.5, elinewidth=0.9,
                label=r"Accuracy (grade $\geq$ 4)", zorder=3)

    # The decline is NOT monotone. Saying so on the figure itself is cheaper
    # than having a reviewer find it, and the paper's subject is calibration.
    # Kept clear of the assertion line at 1.00: at a flat aspect ratio the
    # vertical axis compresses and an annotation near 0.9 collides with it.
    ax.annotate("decline is not monotone", xy=(2.06, 0.52), xytext=(3.05, 0.70),
                fontsize=6.5, color="#475569",
                arrowprops=dict(arrowstyle="->", color="#475569", lw=0.7,
                                shrinkA=0, shrinkB=3))

    ax.set_xticks(x)
    ax.set_xticklabels([LABELS[r] for r in ratios], fontsize=8)
    ax.set_xlabel("Dilution (finetuning : pretraining mix)", fontsize=8.5)
    ax.set_ylabel("Rate", fontsize=8.5)
    ax.set_ylim(-0.04, 1.08)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.tick_params(labelsize=8)
    ax.grid(axis="y", color="#E2E8F0", linewidth=0.6)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    # Legend below the axes: inside the panel it sat on top of the accuracy
    # line, which is the series the figure exists to show.
    ax.legend(fontsize=6.6, loc="upper center", frameon=False, ncol=3,
              bbox_to_anchor=(0.5, -0.30), columnspacing=1.4, handlelength=1.9)

    fig.tight_layout(pad=0.3)
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"figure_ladder.{ext}", bbox_inches="tight")

    assert all(n == ns[0] for n in ns), f"uneven n across rungs: {ns}"
    print(f"n per rung   : {ns[0]}  (total {sum(ns)})")
    print(f"assertion    : {[round(v, 2) for v in a_rate]}")
    print(f"grade >= 4   : {[round(v, 2) for v in g_rate]}")
    print(f"monotone     : {all(g_rate[i] >= g_rate[i+1] for i in range(len(g_rate)-1))}")
    print(f"wrote        : {OUT / 'figure_ladder.pdf'} (+ .png)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
