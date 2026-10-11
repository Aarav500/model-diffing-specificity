"""Every number the camera-ready adds, from files on disk -- PREREG §16.

Reads the original batch (results/) and the Addendum A batch
(results/camera_ready/), and prints each analysis with its status label:
CONFIRMATORY (A.6 family, Holm-corrected), PRE-REGISTERED (§6, overdue), or
EXPLORATORY. Writes results/camera_ready/stats.json so the paper's numbers
have a single code path.

  python -m src.camera_ready_stats
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from scipy.stats import beta, fisher_exact, mannwhitneyu, spearmanr

REPO = Path(__file__).resolve().parent.parent
R = REPO / "results"
CR = R / "camera_ready"
GPT5 = "gpt-5-2025-08-07"
MINI = "gpt-5-mini-2025-08-07"
RUNGS = {"L00": 0.0, "L01": 0.1, "L03": 0.3, "L05": 0.5, "L10": 1.0, "L20": 2.0}
CONF_RANK = {"hedged": 0, "plain": 1, "emphatic": 2}


def jl(path: Path) -> dict:
    out = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                d = json.loads(line)
                out[d["run_id"]] = d
    return out


def cp(k: int, n: int) -> tuple[float, float]:
    """Clopper-Pearson exact 95% interval (PREREG §8)."""
    if n == 0:
        return (float("nan"), float("nan"))
    lo = 0.0 if k == 0 else beta.ppf(0.025, k, n - k + 1)
    hi = 1.0 if k == n else beta.ppf(0.975, k + 1, n - k)
    return (float(lo), float(hi))


def spearman_exact(x, y) -> tuple[float, float]:
    """Spearman rho with an EXACT two-sided permutation p over all orderings.

    The ladder has six rung-level points. scipy's default p uses a
    t-approximation that is anti-conservative at n=6 (0.005 where the exact
    value is 0.017), so every ladder trend in the camera-ready uses this.
    """
    from itertools import permutations
    rho = spearmanr(x, y)[0]
    hits = total = 0
    for perm in permutations(y):
        r = spearmanr(x, perm)[0]
        hits += abs(r) >= abs(rho) - 1e-12
        total += 1
    return float(rho), hits / total


def mwu_perm_less(a, b, n_resamples: int = 100_000) -> float:
    """One-sided permutation p for 'a is lower than b' on the Mann-Whitney U
    statistic. The confidence codes take three values, so ties are heavy and
    groups are small (n=2 to 30); the asymptotic MWU p is unreliable there."""
    import numpy as np
    from scipy.stats import permutation_test
    stat = lambda x, y, axis: mannwhitneyu(x, y, axis=axis).statistic
    res = permutation_test((np.array(a), np.array(b)), stat, alternative="less",
                           n_resamples=n_resamples, random_state=20261010,
                           permutation_type="independent", vectorized=True)
    return float(res.pvalue)


def holm(pvals: dict[str, float]) -> dict[str, float]:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m, adj, running = len(items), {}, 0.0
    for i, (k, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        adj[k] = running
    return adj


def load_runs() -> list[dict]:
    runs = []
    for armmap, grades, corr, reports in (
        (R / ".armmap.json", R / "grades.jsonl", R / "correctness.jsonl", R / "reports"),
        (CR / ".armmap.json", CR / "grades.jsonl", CR / "correctness.jsonl", CR / "reports"),
    ):
        if not armmap.exists():
            continue
        g, c = jl(grades), jl(corr)
        for rid, meta in json.loads(armmap.read_text()).items():
            if rid not in g:
                continue
            rep = json.loads((reports / f"{rid}.json").read_text(encoding="utf-8"))
            runs.append({
                "run_id": rid, "agent": meta.get("agent", GPT5), "arm": meta["arm"],
                "variant": meta["prompt_variant"], "seed": meta["seed"],
                "category": g[rid]["category"], "confidence": g[rid]["confidence"],
                "claim_scope": g[rid].get("claim_scope"),
                "objective": g[rid].get("asserted_objective", ""),
                "grade": c.get(rid, {}).get("grade"),
                "stop_reason": rep.get("stop_reason"), "error": rep.get("error"),
                "batch": "original" if armmap.parent == R else "addendum",
            })
    sem = jl(CR / "semantic.jsonl")
    for r in runs:
        r["semantic"] = sem.get(r["run_id"], {}).get("kind")
    return runs


def cell_table(runs: list[dict]) -> dict:
    cells = defaultdict(list)
    for r in runs:
        cells[(r["agent"], r["arm"], r["variant"])].append(r)
    out = {}
    for key, rs in sorted(cells.items()):
        cat = Counter(r["category"] for r in rs)
        a, b, d = cat["ASSERT"], cat["ABSTAIN"], cat["DEGENERATE"]
        sem = sum(1 for r in rs if r["category"] == "ASSERT" and r["semantic"] == "SEMANTIC")
        conf = Counter(r["confidence"] for r in rs if r["category"] == "ASSERT")
        usable = [r for r in rs if r["category"] in ("ASSERT", "ABSTAIN")]
        strict = sum(1 for r in usable if (r["grade"] or 0) >= 4)
        out["/".join(key)] = {
            "n": len(rs), "assert": a, "abstain": b, "degenerate": d,
            "assert_rate": a / (a + b) if a + b else None, "assert_ci": cp(a, a + b),
            "semantic_assert": sem,
            "semantic_rate": sem / (a + b) if a + b else None, "semantic_ci": cp(sem, a + b),
            "confidence_of_asserts": dict(conf),
            "grade_ge4": strict, "grade_ge4_rate": strict / len(usable) if usable else None,
            "degenerate_reasons": [r["stop_reason"] for r in rs if r["category"] == "DEGENERATE"],
        }
    return out


def fisher_presup_vs_neutral(table: dict, agent: str, arm: str, use_semantic=False):
    p, n = table.get(f"{agent}/{arm}/presup"), table.get(f"{agent}/{arm}/neutral")
    if not p or not n:
        return None
    k = "semantic_assert" if use_semantic else "assert"
    pa, pn = p[k], p["assert"] + p["abstain"]
    na, nn = n[k], n["assert"] + n["abstain"]
    odds, pv = fisher_exact([[pa, pn - pa], [na, nn - na]])
    return {"presup": f"{pa}/{pn}", "neutral": f"{na}/{nn}", "p": pv, "odds": odds}


def main():
    runs = load_runs()
    table = cell_table(runs)
    stats: dict = {"cells": table}

    print("=" * 78)
    print("CELLS  (rate = ASSERT/(ASSERT+ABSTAIN), DEGENERATE excluded; CP 95%)")
    print("=" * 78)
    for k, v in table.items():
        lo, hi = v["assert_ci"]
        extra = ""
        if k.split("/")[1] in ("I0", "R1", "R2", "I0n", "R1n", "R2n"):
            slo, shi = v["semantic_ci"]
            extra = f"  semantic {v['semantic_assert']}/{v['assert'] + v['abstain']} [{slo:.2f},{shi:.2f}]"
        print(f"  {k:<36} {v['assert']:>2}/{v['assert'] + v['abstain']:<2} "
              f"[{lo:.2f},{hi:.2f}]  deg={v['degenerate']}{extra}")

    print("\n" + "=" * 78)
    print("CONFIRMATORY FAMILY (PREREG §16 A.6) -- Fisher exact, presup vs neutral, Holm")
    print("=" * 78)
    fam = {"F1": (GPT5, "I0"), "F2": (GPT5, "R1"), "F3": (GPT5, "R2"), "F4": (MINI, "N0")}
    res = {k: fisher_presup_vs_neutral(table, *v) for k, v in fam.items()}
    present = {k: v["p"] for k, v in res.items() if v}
    adj = holm(present) if present else {}
    for k, (agent, arm) in fam.items():
        v = res[k]
        if not v:
            print(f"  {k} {agent} {arm}: NOT AVAILABLE")
            continue
        v["p_holm"] = adj[k]
        print(f"  {k} {agent:<22} {arm}: presup {v['presup']}  neutral {v['neutral']}  "
              f"p={v['p']:.4g}  Holm p={adj[k]:.4g}")
    stats["confirmatory"] = res

    print("\n  descriptive companion: same contrast on SEMANTIC assertions (A.4)")
    stats["semantic_contrast"] = {}
    for agent in (GPT5, MINI):
        for arm in ("I0", "R1", "R2", "I0n", "R1n", "R2n"):
            v = fisher_presup_vs_neutral(table, agent, arm, use_semantic=True)
            if v:
                stats["semantic_contrast"][f"{agent}/{arm}"] = v
                print(f"    {agent:<22} {arm}: presup {v['presup']}  neutral {v['neutral']}  "
                      f"p={v['p']:.4g}  [descriptive]")

    print("\n" + "=" * 78)
    print("ORIGINAL N0 FRAMING RESULT -- sensitivity to the one DEGENERATE run")
    print("=" * 78)
    sens = {}
    for label, presup in (("as reported, 9/9", (9, 0)), ("degenerate as ASSERT, 10/10", (10, 0)),
                          ("degenerate as ABSTAIN, 9/10", (9, 1))):
        _, pv = fisher_exact([list(presup), [2, 8]])
        sens[label] = pv
        print(f"  {label:<30} vs 2/10   p = {pv:.5f}")
    stats["n0_sensitivity"] = sens
    deg = [r for r in runs if r["batch"] == "original" and r["category"] == "DEGENERATE"]
    for r in deg:
        print(f"  DEGENERATE run {r['run_id']}: arm {r['arm']} {r['variant']} s{r['seed']}, "
              f"stop_reason={r['stop_reason']}")

    print("\n" + "=" * 78)
    print("LADDER BY AGENT  (grade>=4 trend EXPLORATORY, as in the original)")
    print("=" * 78)
    stats["ladder"] = {}
    for agent in (GPT5, MINI):
        rows = []
        for arm, ratio in RUNGS.items():
            rs = [r for r in runs if r["agent"] == agent and r["arm"] == arm]
            usable = [r for r in rs if r["category"] in ("ASSERT", "ABSTAIN")]
            if not usable:
                continue
            a = sum(r["category"] == "ASSERT" for r in usable)
            s = sum((r["grade"] or 0) >= 4 for r in usable)
            emph = sum(r["confidence"] == "emphatic" for r in rs if r["category"] == "ASSERT")
            hedg = sum(r["confidence"] == "hedged" for r in rs if r["category"] == "ASSERT")
            rows.append({"arm": arm, "ratio": ratio, "n": len(usable), "assert": a,
                         "grade_ge4": s, "emphatic": emph, "hedged": hedg,
                         "degenerate": len(rs) - len(usable)})
        if len(rows) < 3:
            continue
        rho, prho = spearman_exact([x["ratio"] for x in rows], [x["grade_ge4"] / x["n"] for x in rows])
        for x in rows:
            rs = [r for r in runs if r["agent"] == agent and r["arm"] == x["arm"]
                  and r["category"] in ("ASSERT", "ABSTAIN")]
            x["grade_ge2"] = sum((r["grade"] or 0) >= 2 for r in rs)
        f_odds, f_p = fisher_exact([[rows[0]["grade_ge4"], rows[0]["n"] - rows[0]["grade_ge4"]],
                                    [rows[-1]["grade_ge4"], rows[-1]["n"] - rows[-1]["grade_ge4"]]])
        stats["ladder"][agent] = {"rows": rows, "spearman_rho": rho, "spearman_p": prho,
                                  "fisher_endpoints_p": f_p}
        print(f"  {agent}")
        for x in rows:
            print(f"    {x['arm']} 1:{x['ratio']:<4} assert {x['assert']:>2}/{x['n']:<2} "
                  f"grade>=4 {x['grade_ge4']:>2}/{x['n']:<2}  emphatic {x['emphatic']:>2} "
                  f"hedged {x['hedged']:>2}  deg {x['degenerate']}")
        print(f"    grade>=2: {sum(x['grade_ge2'] for x in rows)}/{sum(x['n'] for x in rows)}")
        print(f"    Spearman rho={rho:.3f} exact p={prho:.4f}; endpoints Fisher p={f_p:.5f} [EXPLORATORY]")

    print("\n" + "=" * 78)
    print("§6 (PRE-REGISTERED, never reported): confidence of ASSERTs, nulls vs positives")
    print("=" * 78)
    stats["s6"] = {}

    def conf_of(agent, arms, variant=None):
        return [CONF_RANK[r["confidence"]] for r in runs
                if r["agent"] == agent and r["arm"] in arms and r["category"] == "ASSERT"
                and (variant is None or r["variant"] == variant)]

    for variant in ("presup", "neutral", None):
        tag = variant or "both framings"
        pos = conf_of(GPT5, {"P"}, variant)
        for label, arms in (("registered nulls N1+N2", {"N1", "N2"}), ("N0", {"N0"}),
                            ("synthetic nulls I0+R1+R2", {"I0", "R1", "R2"})):
            nul = conf_of(GPT5, arms, variant)
            if not nul or not pos:
                continue
            u, pu = mannwhitneyu(nul, pos, alternative="less")
            pp = mwu_perm_less(nul, pos)
            cn, cpz = Counter(nul), Counter(pos)
            stats["s6"][f"{tag}/{label}"] = {
                "null": {k: cn[v] for k, v in CONF_RANK.items()},
                "positive_P": {k: cpz[v] for k, v in CONF_RANK.items()},
                "mannwhitney_less_p": pu, "permutation_less_p": pp}
            print(f"  {tag:<14} {label:<26} null h/p/e={cn[0]}/{cn[1]}/{cn[2]}  "
                  f"P h/p/e={cpz[0]}/{cpz[1]}/{cpz[2]}  one-sided MWU p={pu:.3f}  "
                  f"permutation p={pp:.3f}")

    print("\n  EXPLORATORY: within the gpt-5 ladder, accuracy (grade>=4) by verbal confidence")
    stats["ladder_conf_acc"] = {}
    for variant in ("presup", "neutral"):
        for level in ("hedged", "plain", "emphatic"):
            rs = [r for r in runs if r["agent"] == GPT5 and r["arm"] in RUNGS
                  and r["variant"] == variant and r["category"] == "ASSERT"
                  and r["confidence"] == level]
            if rs:
                k = sum((r["grade"] or 0) >= 4 for r in rs)
                stats["ladder_conf_acc"][f"{variant}/{level}"] = [k, len(rs)]
                print(f"    {variant:<8} {level:<9} grade>=4 {k:>2}/{len(rs):<3} = {k / len(rs):.2f}")
        rs = [r for r in runs if r["agent"] == GPT5 and r["arm"] in RUNGS
              and r["variant"] == variant and r["category"] == "ASSERT"]
        if rs:
            rho, pr = spearmanr([CONF_RANK[r["confidence"]] for r in rs],
                                [1 if (r["grade"] or 0) >= 4 else 0 for r in rs])
            stats["ladder_conf_acc"][f"{variant}/spearman"] = [rho, pr]
            print(f"    {variant:<8} Spearman(confidence, correct) rho={rho:.3f} p={pr:.3f}")

    print("\n" + "=" * 78)
    print("ADDENDUM B (PREREG §17): synthetic nulls with vs without Patchscope [descriptive]")
    print("=" * 78)
    stats["addendum_b"] = {}
    for agent in (GPT5, MINI):
        for arm in ("I0", "R1", "R2"):
            for variant in ("presup", "neutral"):
                w, wo = table.get(f"{agent}/{arm}/{variant}"), table.get(f"{agent}/{arm}n/{variant}")
                if not w or not wo:
                    continue
                f = fisher_presup_vs_neutral(table, agent, arm + "n")
                stats["addendum_b"][f"{agent}/{arm}/{variant}"] = {
                    "with_patchscope": [w["assert"], w["assert"] + w["abstain"]],
                    "without_patchscope": [wo["assert"], wo["assert"] + wo["abstain"]],
                    "without_semantic": wo["semantic_assert"],
                    "without_ci": wo["assert_ci"],
                }
                print(f"  {agent:<22} {arm:<3} {variant:<8} with {w['assert']}/{w['assert'] + w['abstain']}"
                      f"  without {wo['assert']}/{wo['assert'] + wo['abstain']}"
                      f" (semantic {wo['semantic_assert']})"
                      + (f"   presup-vs-neutral p={f['p']:.3g} [exploratory]" if f and variant == 'presup' else ""))

    print("\n  pooled assertion, every usable run (abstract-level counts)")
    stats["pooled"] = {}
    for agent in (GPT5, MINI):
        for variant in ("presup", "neutral"):
            for label, exclude in (("with-Patchscope nulls", {"I0n", "R1n", "R2n"}),
                                   ("matched nulls", {"I0", "R1", "R2"})):
                a = n = 0
                for k, v in table.items():
                    ag, arm, var = k.split("/")
                    if ag == agent and var == variant and arm not in exclude:
                        a += v["assert"]; n += v["assert"] + v["abstain"]
                stats["pooled"][f"{agent}/{variant}/{label}"] = [a, n]
                print(f"    {agent:<22} {variant:<8} 13 arms, {label:<22} {a}/{n}")

    print("\n" + "=" * 78)
    print("CONSISTENCY: original judge vs clean-prompt judge (A.5)")
    print("=" * 78)
    orig_old = json.loads((R / "consistency.json").read_text()) if (R / "consistency.json").exists() else {}
    orig_new = json.loads((CR / "consistency_original.json").read_text()) \
        if (CR / "consistency_original.json").exists() else {}
    clean = json.loads((CR / "consistency_clean.json").read_text()) \
        if (CR / "consistency_clean.json").exists() else {}
    stats["consistency"] = {}
    for name, v in sorted(clean.items()):
        if "consistency_values" not in v:
            continue
        agent, arm, variant = name.split("/")
        o = None
        if agent == GPT5 and f"{arm}/{variant}" in orig_old:
            o = orig_old[f"{arm}/{variant}"].get("consistency")
        elif name in orig_new:
            o = orig_new[name].get("median")
        stats["consistency"][name] = {"original": o, "clean": v["consistency_values"],
                                      "n_assertions": v["n_assertions"]}
        print(f"  {name:<40} n={v['n_assertions']:>2}  original={o if o is None else round(o, 2)}  "
              f"clean={[round(x, 2) for x in v['consistency_values']]}")

    if (CR / "noise_calibration.json").exists():
        stats["noise_calibration"] = json.loads((CR / "noise_calibration.json").read_text())
        nc = stats["noise_calibration"]
        print(f"\nnoise: R1 c=1 mean cell norm {nc['R1']['mean_cell_norm']:.1f}; "
              f"R2 c={nc['R2']['c']:.3f} mean cell norm {nc['R2']['mean_cell_norm']:.1f} "
              f"(P target {nc['p_target_norm']:.1f})")

    usage = defaultdict(lambda: [0, 0, 0])
    for p in sorted((CR / "reports").glob("run_*.json")) if (CR / "reports").exists() else []:
        d = json.loads(p.read_text(encoding="utf-8"))
        u = usage[d["model"]]
        u[0] += 1; u[1] += d["input_tokens"]; u[2] += d["output_tokens"]
    stats["usage"] = {k: {"runs": v[0], "input_tokens": v[1], "output_tokens": v[2]}
                      for k, v in usage.items()}

    CR.mkdir(parents=True, exist_ok=True)
    (CR / "stats.json").write_text(json.dumps(stats, indent=2, default=str))
    print(f"\nwrote {CR / 'stats.json'}")


if __name__ == "__main__":
    main()
