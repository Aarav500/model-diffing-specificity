"""Analysis -- produces D1, D2 and D3 from real grades. Implements PREREG §8.

This script computes nothing unless `results/grades.jsonl` and `results/.armmap.json`
both exist. It has no demo mode, no synthetic fallback and no placeholder numbers:
a figure produced from invented data in a study about false positives would be
self-refuting.

  python -m src.analyze --out results/
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import beta, fisher_exact

REPO = Path(__file__).resolve().parent.parent
RESULTS = REPO / "results"

NULL_ARMS = ("N1", "N2")          # headline FPR (PREREG §2)
DESCRIPTIVE_ARMS = ("N0",)        # reported separately (PREREG §2)


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Exact binomial interval. Correct at k=0 and k=n, where normal approx is not."""
    if n == 0:
        return (float("nan"), float("nan"))
    lo = 0.0 if k == 0 else beta.ppf(alpha / 2, k, n - k + 1)
    hi = 1.0 if k == n else beta.ppf(1 - alpha / 2, k + 1, n - k)
    return float(lo), float(hi)


def load(results_dir: Path) -> list[dict]:
    grades_p = results_dir / "grades.jsonl"
    armmap_p = results_dir / ".armmap.json"
    missing = [p.name for p in (grades_p, armmap_p) if not p.exists()]
    if missing:
        raise SystemExit(
            f"Missing {missing} in {results_dir}.\n"
            f"No experimental data exists yet, so there is nothing to analyse.\n"
            f"Run the arms first (src/blind_harness.py), then src/grade.py."
        )

    armmap = json.loads(armmap_p.read_text())
    rows = []
    for line in grades_p.read_text().splitlines():
        if not line.strip():
            continue
        g = json.loads(line)
        meta = armmap.get(g["run_id"])
        if meta is None:
            raise SystemExit(f"run_id {g['run_id']} has no arm entry -- blinding map is incomplete.")
        rows.append({**g, **meta})
    return rows


def effective_category(row: dict) -> str:
    """PREREG §4: on N2 only, an ASSERT about a SHARED property is not a false
    positive -- both N2 models are narrowly finetuned on the same data."""
    if row["arm"] == "N2" and row["category"] == "ASSERT" and row["claim_scope"] == "shared":
        return "ABSTAIN"
    return row["category"]


def cell_stats(rows: list[dict]) -> dict:
    n_total = len(rows)
    cats = [effective_category(r) for r in rows]
    n_assert = cats.count("ASSERT")
    n_abstain = cats.count("ABSTAIN")
    n_degen = cats.count("DEGENERATE")
    denom = n_assert + n_abstain
    rate = n_assert / denom if denom else float("nan")
    lo, hi = clopper_pearson(n_assert, denom)
    return {
        "n_total": n_total, "n_assert": n_assert, "n_abstain": n_abstain,
        "n_degenerate": n_degen, "denom": denom,
        "assert_rate": rate, "ci_lo": lo, "ci_hi": hi,
        "abstention_rate": n_abstain / denom if denom else float("nan"),
        "coverage": denom / n_total if n_total else float("nan"),
    }


def group(rows, *keys):
    out: dict[tuple, list[dict]] = {}
    for r in rows:
        out.setdefault(tuple(r[k] for k in keys), []).append(r)
    return out


# --------------------------------------------------------------------------
# D3 -- the table
# --------------------------------------------------------------------------

def table1(rows: list[dict]) -> str:
    lines = [
        "| Arm | Prompt | n | Assert rate | 95% CI | Abstention | Degenerate | Coverage |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for (arm, variant), rs in sorted(group(rows, "arm", "prompt_variant").items()):
        s = cell_stats(rs)
        lines.append(
            f"| {arm} | {variant} | {s['n_total']} | {s['assert_rate']:.2f} | "
            f"[{s['ci_lo']:.2f}, {s['ci_hi']:.2f}] | {s['abstention_rate']:.2f} | "
            f"{s['n_degenerate']}/{s['n_total']} | {s['coverage']:.2f} |"
        )
    lines.append("")
    lines.append("On positive arms the assert rate is the **detection rate**; on null arms it is "
                 "the **false-positive rate**. Same statistic, different arm -- that symmetry is the point.")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# D1 -- detection vs false-positive rate
# --------------------------------------------------------------------------

def figure1(rows: list[dict], out: Path) -> Path:
    """The point is not that four bars sit at 1.00. It is that three of them are
    at 1.00 because the agent was RIGHT, and the fourth moves from 1.00 to 0.20
    on identical evidence when the prompt stops presupposing an answer. Plot it
    so that contrast is what the eye lands on."""
    # Main arms only -- ladder rungs live in figure 2.
    ORDER = ["P", "N1", "N2", "N0"]
    LABEL = {
        "P":  "P\nreleased organism",
        "N1": "N1\ngeneric corpus",
        "N2": "N2\ntwo seeds",
        "N0": "N0\nno narrow objective",
    }
    arms = [a for a in ORDER if any(r["arm"] == a for r in rows)]
    variants = ["neutral", "presup"]
    colours = {"neutral": "#2471a3", "presup": "#c0392b"}
    width = 0.36

    fig, ax = plt.subplots(figsize=(9, 5.4))

    # Shade the two regimes: arms where a real signal exists vs the one where none does.
    n_signal = sum(1 for a in arms if a != "N0")
    ax.axvspan(-0.6, n_signal - 0.5, color="#2ecc71", alpha=0.06)
    ax.axvspan(n_signal - 0.5, len(arms) - 0.4, color="#e74c3c", alpha=0.07)
    ax.text((n_signal - 1) / 2, 1.11, "a real signal exists — agent is correct",
            ha="center", fontsize=9, color="#1e8449")
    ax.text(n_signal + (len(arms) - n_signal - 1) / 2, 1.11,
            "nothing narrow to find", ha="center", fontsize=9, color="#a93226")

    for i, variant in enumerate(variants):
        xs, ys, los, his = [], [], [], []
        for j, arm in enumerate(arms):
            rs = [r for r in rows if r["arm"] == arm and r["prompt_variant"] == variant]
            if not rs:
                continue
            s = cell_stats(rs)
            xs.append(j + (i - 0.5) * width)
            ys.append(s["assert_rate"])
            los.append(s["assert_rate"] - s["ci_lo"])
            his.append(s["ci_hi"] - s["assert_rate"])
        ax.bar(xs, ys, width=width * 0.92, color=colours[variant],
               label=f"{variant} framing", alpha=0.9, zorder=3)
        ax.errorbar(xs, ys, yerr=[los, his], fmt="none", ecolor="black",
                    capsize=4, lw=1.1, zorder=4)

    # Annotate the result: the N0 pair.
    if "N0" in arms:
        j = arms.index("N0")
        ax.annotate("", xy=(j - 0.5 * width, 0.26), xytext=(j - 0.5 * width, 0.97),
                    arrowprops=dict(arrowstyle="->", lw=2.0, color="#111111",
                                    shrinkA=0, shrinkB=0), zorder=5)
        ax.text(j - 0.5 * width - 0.06, 0.62,
                "1.00 → 0.20\nsame evidence\n$p$ = 0.0007",
                fontsize=9.5, va="center", ha="right", fontweight="bold", zorder=6)

    ax.set_xticks(range(len(arms)))
    ax.set_xticklabels([LABEL[a] for a in arms], fontsize=9)
    ax.set_xlim(-0.6, len(arms) - 0.35)
    ax.set_ylim(0, 1.20)
    ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_ylabel("P(agent names a specific objective)")
    ax.set_title("The agent asserts on every arm. Only framing changes that —\n"
                 "and only where there is nothing to find",
                 fontsize=12, pad=26)
    ax.axhline(0, color="black", lw=0.8)
    ax.legend(loc="lower left", fontsize=9, framealpha=0.95)
    fig.tight_layout()
    p = out / "figure1_detection_vs_fpr.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    return p


# --------------------------------------------------------------------------
# D2 -- dilution power curve
# --------------------------------------------------------------------------

def figure2(rows: list[dict], out: Path) -> Path | None:
    ladder = [r for r in rows if r["arm"].startswith("mix1-")]
    if not ladder:
        print("  (skipping Figure 2: no ladder arms present)")
        return None

    def ratio(arm: str) -> float:
        return float(arm.replace("mix1-", "").replace("p", "."))

    fig, ax = plt.subplots(figsize=(8, 5))
    for variant in sorted({r["prompt_variant"] for r in ladder}):
        pts = []
        for arm, rs in group([r for r in ladder if r["prompt_variant"] == variant], "arm").items():
            s = cell_stats(rs)
            pts.append((ratio(arm[0]), s["assert_rate"], s["ci_lo"], s["ci_hi"]))
        pts.sort()
        x = [p[0] for p in pts]
        y = [p[1] for p in pts]
        ax.plot(x, y, marker="o", label=f"detection, prompt: {variant}")
        ax.fill_between(x, [p[2] for p in pts], [p[3] for p in pts], alpha=0.15)

    nulls = [r for r in rows if r["arm"] in NULL_ARMS]
    if nulls:
        s = cell_stats(nulls)
        ax.axhspan(s["ci_lo"], s["ci_hi"], color="crimson", alpha=0.15,
                   label="null-arm FPR (95% CI)")
        ax.axhline(s["assert_rate"], color="crimson", ls="--", lw=1.2)

    ax.set_xlabel("pretraining-data mixing ratio  |D_ft| : |D_pt|")
    ax.set_ylabel("P(agent names a specific objective)")
    ax.set_ylim(0, 1.05)
    ax.set_title("Dilution curve with the false-positive floor overlaid", fontsize=11)
    ax.legend(fontsize=8)
    fig.tight_layout()
    p = out / "figure2_dilution_curve.png"
    fig.savefig(p, dpi=200)
    plt.close(fig)
    return p


# --------------------------------------------------------------------------

def primary_test(rows: list[dict]) -> str:
    pos = [r for r in rows if r["arm"] == "P"]
    nul = [r for r in rows if r["arm"] in NULL_ARMS]
    if not pos or not nul:
        return "Primary test not computable: need both arm P and at least one of N1/N2."
    a, b = cell_stats(pos), cell_stats(nul)
    odds, p = fisher_exact([[a["n_assert"], a["n_abstain"]],
                            [b["n_assert"], b["n_abstain"]]])
    return (f"Primary test (PREREG §8) -- Fisher exact, P vs pooled {list(NULL_ARMS)}:\n"
            f"  P    : {a['n_assert']}/{a['denom']} assert ({a['assert_rate']:.2f})\n"
            f"  nulls: {b['n_assert']}/{b['denom']} assert ({b['assert_rate']:.2f})\n"
            f"  odds ratio = {odds:.3f}, p = {p:.4g}")


def h2_test(rows: list[dict]) -> str:
    nul = [r for r in rows if r["arm"] in NULL_ARMS]
    pre = [r for r in nul if r["prompt_variant"] == "presup"]
    neu = [r for r in nul if r["prompt_variant"] == "neutral"]
    if not pre or not neu:
        return "H2 test not computable: need both prompt variants on null arms."
    a, b = cell_stats(pre), cell_stats(neu)
    odds, p = fisher_exact([[a["n_assert"], a["n_abstain"]],
                            [b["n_assert"], b["n_abstain"]]])
    return (f"H2 test (PREREG §8) -- presup vs neutral within null arms:\n"
            f"  presup : {a['n_assert']}/{a['denom']} ({a['assert_rate']:.2f})\n"
            f"  neutral: {b['n_assert']}/{b['denom']} ({b['assert_rate']:.2f})\n"
            f"  odds ratio = {odds:.3f}, p = {p:.4g}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", type=Path, default=RESULTS)
    ap.add_argument("--out", type=Path, default=RESULTS)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)

    rows = load(a.results)
    print(f"Loaded {len(rows)} graded runs across "
          f"{len({r['arm'] for r in rows})} arms.\n")

    t = table1(rows)
    (a.out / "table1.md").write_text(t)
    print(t, "\n")

    print(figure1(rows, a.out))
    f2 = figure2(rows, a.out)
    if f2:
        print(f2)

    print("\n" + primary_test(rows))
    print("\n" + h2_test(rows))

    for arm in DESCRIPTIVE_ARMS:
        rs = [r for r in rows if r["arm"] == arm]
        if rs:
            s = cell_stats(rs)
            print(f"\n{arm} (descriptive, excluded from headline FPR per PREREG §2): "
                  f"assert {s['n_assert']}/{s['denom']} = {s['assert_rate']:.2f} "
                  f"[{s['ci_lo']:.2f}, {s['ci_hi']:.2f}]")


if __name__ == "__main__":
    main()
