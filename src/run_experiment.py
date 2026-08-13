"""Run the full blind experiment: every (arm x prompt x seed) cell.

Implements PREREGISTRATION.md §3 (blinding) and §8 (sample sizes).

Run order is INTERLEAVED across arms rather than arm-by-arm, so that any drift
in the judge model over the run affects every arm equally (§3.6). With a thread
pool the ordering would be roughly interleaved anyway; it is made explicit so
the property does not depend on scheduler luck.

Resume-safe: run_cell skips a cell whose report already exists, so an
interrupted run continues rather than re-billing completed cells.

  python -m src.run_experiment --seeds 10
  python -m src.run_experiment --seeds 10 --arms P,N0,N1,N2 --workers 6
"""

from __future__ import annotations

import argparse
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Fixed in source. Run IDs are deterministic given the salt, so a re-run
# produces the same IDs and resumes cleanly; the salt keeps the ID itself
# uninformative about the arm.
SALT = "mats-sprint-2026-08-12"

PROMPTS = ("presup", "neutral")


def build_schedule(arms, prompts, seeds):
    """Interleave: all arms at seed 0, then all arms at seed 1, ..."""
    out = []
    for seed in range(seeds):
        for prompt in prompts:
            for arm in arms:
                out.append((arm, prompt, seed))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default="P,N0,N1,N2")
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", type=Path, default=REPO / "results" / "reports")
    a = ap.parse_args()

    from src import blind_harness as bh
    from src import llm

    arms = [s.strip() for s in a.arms.split(",") if s.strip()]
    llm.require_key(bh.AGENT_MODEL)

    missing = [arm for arm in arms
               if not (REPO / "results" / "artifacts" / arm / "artifacts.json").exists()]
    if missing:
        raise SystemExit(f"No artifacts for arms: {missing}")

    schedule = build_schedule(arms, PROMPTS, a.seeds)
    print(f"agent   : {bh.AGENT_MODEL}")
    print(f"arms    : {arms}")
    print(f"cells   : {len(arms)} arms x {len(PROMPTS)} prompts x {a.seeds} seeds "
          f"= {len(schedule)} runs")
    print(f"workers : {a.workers}")
    print(f"order   : interleaved across arms (PREREG §3.6)\n")

    def one(task):
        arm, prompt, seed = task
        art = REPO / "results" / "artifacts" / arm / "artifacts.json"
        return arm, prompt, seed, bh.run_cell(art, arm, prompt, seed, SALT, a.out)

    t0 = time.time()
    done = err = 0
    tok_in = tok_out = tok_cached = 0

    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futures = [ex.submit(one, t) for t in schedule]
        for f in as_completed(futures):
            try:
                arm, prompt, seed, run = f.result()
            except Exception as e:
                err += 1
                print(f"  [{done+err:>3}/{len(schedule)}] EXCEPTION {type(e).__name__}: {e}")
                continue
            done += 1
            tok_in += run.input_tokens
            tok_out += run.output_tokens
            tok_cached += run.cached_tokens
            flag = f"  ERROR {run.error[:60]}" if run.error else ""
            # Arm is printed for operator progress only. The agent never saw it,
            # and the grader runs from the report text alone in a separate pass.
            print(f"  [{done+err:>3}/{len(schedule)}] {run.run_id}  "
                  f"{arm:<3} {prompt:<7} s{seed}  "
                  f"in={run.input_tokens:>5} out={run.output_tokens:>5} "
                  f"cached={run.cached_tokens:>5}{flag}")

    dt = time.time() - t0
    print(f"\ndone: {done} ok, {err} failed, {dt/60:.1f} min")
    print(f"tokens: in={tok_in:,} out={tok_out:,} cached={tok_cached:,} "
          f"({100*tok_cached/max(1,tok_in):.0f}% of input served from cache)")
    print(f"\nreports -> {a.out}")
    print("next: python -m src.grade --reports results/reports --out results/grades.jsonl")


if __name__ == "__main__":
    main()
