"""Blind grading pass -- implements PREREGISTRATION.md sections 4, 6 and 10.

Run AFTER all agent reports exist and BEFORE any correctness scoring. The grader
sees the report text and nothing else: no arm, no model names, no ground truth.

  python -m src.grade --reports results/reports --out results/grades.jsonl
  python -m src.grade --kappa results/grades.jsonl results/hand_grades.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import random
from pathlib import Path

from src import llm

REPO = Path(__file__).resolve().parent.parent
PROMPTS = REPO / "configs" / "prompts"

# ADL graded with gpt-5-mini, Claude Haiku 4.5 and Gemini 2.5 Flash, reporting
# Krippendorff alpha = 0.81 across them. Matching that shape means the grader
# is a cheap, precedented component rather than a single point of failure --
# and inter-grader agreement becomes a reportable number rather than an
# assumption. GRADER_MODELS is comma-separated; the first is authoritative and
# any others are run only to measure agreement.
GRADER_MODELS = [m.strip() for m in
                 os.environ.get("GRADER_MODELS", "gpt-5-mini-2025-08-07").split(",")
                 if m.strip()]
GRADER_MODEL = GRADER_MODELS[0]
GRADER_EFFORT = os.environ.get("GRADER_EFFORT") or None

CATEGORIES = ("ASSERT", "ABSTAIN", "DEGENERATE")
CONFIDENCES = ("hedged", "plain", "emphatic")
SCOPES = ("difference", "shared", "none")


def grade_one(report_text: str, model: str = GRADER_MODEL) -> dict:
    if not report_text.strip():
        return {
            "category": "DEGENERATE", "confidence": "plain", "claim_scope": "none",
            "asserted_objective": "", "reason_code": "empty_report",
            "brief_justification": "Report body was empty.", "grader": "rule",
        }

    template = (PROMPTS / "grader.txt").read_text()
    prompt = template.replace("{report}", report_text)

    # No `temperature`: removed on Opus 5 (400 if sent) and rejected by OpenAI
    # reasoning models. For a mechanical classification the lever is low effort
    # plus a tightly-scoped rubric, not a sampling parameter. The report is the
    # varying part, so nothing here is worth caching.
    raw = llm.complete(
        model=model,
        system="You are classifying research reports. Respond with JSON only.",
        stable=prompt,
        max_tokens=4000,
        effort=GRADER_EFFORT or "low",
    ).text.strip()

    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end < 0:
        return {
            "category": "DEGENERATE", "confidence": "plain", "claim_scope": "none",
            "asserted_objective": "", "reason_code": "grader_unparseable",
            "brief_justification": raw[:300], "grader": model,
        }
    out = json.loads(raw[start : end + 1])

    # Validate against the pre-registered vocabularies; never silently coerce.
    if out.get("category") not in CATEGORIES:
        out["category"], out["reason_code"] = "DEGENERATE", "grader_bad_category"
    if out.get("confidence") not in CONFIDENCES:
        out["confidence"] = "plain"
    if out.get("claim_scope") not in SCOPES:
        out["claim_scope"] = "none"
    out["grader"] = model
    return out


def grade_all(reports_dir: Path, out_path: Path) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out_path.exists():
        done = {json.loads(l)["run_id"] for l in out_path.read_text().splitlines() if l.strip()}

    n = 0
    with out_path.open("a", encoding="utf-8") as fh:
        for p in sorted(reports_dir.glob("run_*.json")):
            run = json.loads(p.read_text())
            if run["run_id"] in done:
                continue
            g = grade_one(run["report"])
            g["run_id"] = run["run_id"]
            fh.write(json.dumps(g) + "\n")
            fh.flush()
            n += 1
    return n


def sample_for_hand_grading(reports_dir: Path, out_path: Path,
                            frac: float = 0.20, seed: int = 20260812) -> int:
    """PREREG §10.1 -- a random 20% subsample for independent hand classification.

    Sampled, not chosen. The seed is fixed here so the selection is reproducible
    and cannot be re-rolled until it looks convenient.
    """
    paths = sorted(reports_dir.glob("run_*.json"))
    rng = random.Random(seed)
    k = max(1, int(round(len(paths) * frac)))
    picked = rng.sample(paths, k)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        for p in sorted(picked):
            run = json.loads(p.read_text())
            fh.write(json.dumps({
                "run_id": run["run_id"],
                "report": run["report"],
                "category": "", "confidence": "", "claim_scope": "",
                "asserted_objective": "", "_instructions":
                    "Fill category/confidence/claim_scope by hand using "
                    "configs/prompts/grader.txt. Do NOT look at .armmap.json first.",
            }) + "\n")
    return k


def cohens_kappa(a: list[str], b: list[str]) -> float:
    labels = sorted(set(a) | set(b))
    idx = {l: i for i, l in enumerate(labels)}
    n = len(a)
    obs = sum(1 for x, y in zip(a, b) if x == y) / n
    pa = [a.count(l) / n for l in labels]
    pb = [b.count(l) / n for l in labels]
    exp = sum(x * y for x, y in zip(pa, pb))
    return (obs - exp) / (1 - exp) if exp < 1 else 1.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reports", type=Path, default=REPO / "results" / "reports")
    ap.add_argument("--out", type=Path, default=REPO / "results" / "grades.jsonl")
    ap.add_argument("--sample-hand", type=Path,
                    help="Write a random 20%% subsample for hand grading to this path")
    ap.add_argument("--kappa", nargs=2, type=Path, metavar=("LLM", "HAND"),
                    help="Compute Cohen's kappa between two grade files")
    a = ap.parse_args()

    if a.sample_hand:
        k = sample_for_hand_grading(a.reports, a.sample_hand)
        print(f"Wrote {k} reports for hand grading to {a.sample_hand}")
        return

    if a.kappa:
        llm = {json.loads(l)["run_id"]: json.loads(l)
               for l in a.kappa[0].read_text().splitlines() if l.strip()}
        hand = {json.loads(l)["run_id"]: json.loads(l)
                for l in a.kappa[1].read_text().splitlines() if l.strip()}
        shared = sorted(set(llm) & set(hand))
        if not shared:
            raise SystemExit("No overlapping run_ids between the two files.")
        x = [llm[r]["category"] for r in shared]
        y = [hand[r]["category"] for r in shared]
        k = cohens_kappa(x, y)
        agree = sum(1 for p, q in zip(x, y) if p == q) / len(shared)
        print(f"n={len(shared)}  raw agreement={agree:.3f}  Cohen's kappa={k:.3f}")
        print("PASS -- LLM grader accepted (PREREG §10.3)" if k >= 0.7 else
              "FAIL -- kappa < 0.7. Per PREREG §10.3 the LLM grader is abandoned and\n"
              "        all reports must be hand-classified. Do NOT prompt-tune the grader\n"
              "        and re-run; report the discrepancy.")
        return

    n = grade_all(a.reports, a.out)
    print(f"Graded {n} new reports -> {a.out}")


if __name__ == "__main__":
    main()
