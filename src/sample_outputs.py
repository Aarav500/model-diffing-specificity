"""D5 -- randomly sampled raw agent outputs.

Sampled, not chosen. The sampling method is stated in the output file itself so a
reader can verify the selection was not curated, and the RNG seed is fixed in
source so it cannot be re-rolled until the examples look good.

Stratified by arm so that every arm is represented, including the ones whose
outputs are least flattering. Within each stratum the draw is uniform.

  python -m src.sample_outputs --per-arm 3 --out results/D5_sampled_outputs.md
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RESULTS = REPO / "results"

# Fixed in source, not passed on the command line. Changing it is a visible diff.
SAMPLING_SEED = 20260812


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", type=Path, default=RESULTS)
    ap.add_argument("--reports", type=Path, default=RESULTS / "reports")
    ap.add_argument("--per-arm", type=int, default=3)
    ap.add_argument("--out", type=Path, default=RESULTS / "D5_sampled_outputs.md")
    a = ap.parse_args()

    armmap_p = a.results / ".armmap.json"
    if not armmap_p.exists():
        raise SystemExit(
            f"{armmap_p} does not exist. No runs have been executed, so there are "
            f"no outputs to sample. This script does not fabricate examples."
        )
    armmap = json.loads(armmap_p.read_text())

    grades = {}
    gp = a.results / "grades.jsonl"
    if gp.exists():
        for line in gp.read_text().splitlines():
            if line.strip():
                g = json.loads(line)
                grades[g["run_id"]] = g

    by_arm: dict[str, list[dict]] = {}
    for p in sorted(a.reports.glob("run_*.json")):
        run = json.loads(p.read_text())
        meta = armmap.get(run["run_id"])
        if meta:
            by_arm.setdefault(meta["arm"], []).append({**run, **meta})

    if not by_arm:
        raise SystemExit("No reports found. Nothing to sample.")

    rng = random.Random(SAMPLING_SEED)
    lines = [
        "# D5 — Randomly sampled raw agent outputs",
        "",
        "## Sampling method",
        "",
        f"Stratified by arm, uniform within stratum, **{a.per_arm} per arm**, "
        f"RNG seed `{SAMPLING_SEED}` fixed in `src/sample_outputs.py`.",
        "",
        "These outputs were **sampled, not chosen**. No output was inspected before "
        "selection and none was excluded after. The seed is hard-coded in source so "
        "that re-rolling the draw would appear as a diff. Every arm is represented, "
        "including those whose outputs are least favourable to the hypothesis.",
        "",
        "Population sampled from:",
        "",
    ]
    for arm in sorted(by_arm):
        lines.append(f"- `{arm}`: {len(by_arm[arm])} runs")
    lines.append("")

    for arm in sorted(by_arm):
        pool = by_arm[arm]
        k = min(a.per_arm, len(pool))
        picked = rng.sample(pool, k)
        lines.append(f"---\n\n## Arm `{arm}` — {k} of {len(pool)} runs\n")
        for run in picked:
            g = grades.get(run["run_id"], {})
            lines.append(f"### `{run['run_id']}`  ·  prompt `{run['prompt_variant']}`  ·  seed {run['seed']}")
            lines.append("")
            if g:
                lines.append(
                    f"**Blind grade:** {g.get('category','?')} · "
                    f"confidence {g.get('confidence','?')} · "
                    f"scope {g.get('claim_scope','?')}"
                    + (f" · asserted: _{g['asserted_objective']}_"
                       if g.get("asserted_objective") else "")
                )
                lines.append("")
            body = run["report"].strip() or "*(empty report)*"
            lines.append("```")
            lines.append(body)
            lines.append("```")
            lines.append("")

    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text("\n".join(lines), encoding="utf-8")
    total = sum(min(a.per_arm, len(v)) for v in by_arm.values())
    print(f"Wrote {total} sampled outputs across {len(by_arm)} arms -> {a.out}")


if __name__ == "__main__":
    main()
