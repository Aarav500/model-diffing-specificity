"""Pilot: one agent call + one grader call, end to end.

PURPOSE IS MECHANICAL VALIDATION, NOT DATA. Writes to results/pilot/, never to
results/reports/, and never touches .armmap.json -- so it cannot leak into the
analysis. Pilot runs are excluded from every rate in PREREGISTRATION.md by
construction, and the deviation is logged there.

Checks, in order:
  1. evidence renders and passes the blinding scrub
  2. the agent returns a non-empty, non-truncated report
  3. the grader returns JSON that validates against the pre-registered vocabularies
  4. token accounting reads back so the cost model is grounded

  python -m src.pilot --arm N0 --prompt presup
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="N0")
    ap.add_argument("--prompt", default="presup", choices=["presup", "neutral"])
    a = ap.parse_args()

    from src import blind_harness as bh
    from src import grade as gr
    from src import llm

    art_p = REPO / "results" / "artifacts" / a.arm / "artifacts.json"
    if not art_p.exists():
        raise SystemExit(f"No artifacts for arm {a.arm} at {art_p}")

    llm.require_key(bh.AGENT_MODEL)
    llm.require_key(gr.GRADER_MODEL)

    art = json.loads(art_p.read_text(encoding="utf-8"))
    evidence = bh.render_evidence(art)
    print(f"[1] evidence rendered: {len(evidence)} chars")
    bh.assert_no_leak(evidence)
    print("[1] blinding scrub: PASS")

    print(f"[2] calling agent {bh.AGENT_MODEL} (prompt={a.prompt}) ...")
    c = bh.call_agent(evidence, a.prompt, seed=0)
    print(f"[2] stop_reason={c.stop_reason}  in={c.input_tokens} "
          f"out={c.output_tokens} cached={c.cached_tokens}")
    if not c.text.strip():
        raise SystemExit("[2] FAIL: agent returned empty text")
    if c.stop_reason in ("length", "max_tokens"):
        print("[2] WARNING: report was truncated -- raise max_tokens")

    print(f"[3] grading with {gr.GRADER_MODEL} ...")
    g = gr.grade_one(c.text, model=gr.GRADER_MODEL)
    ok = (g.get("category") in gr.CATEGORIES
          and g.get("confidence") in gr.CONFIDENCES
          and g.get("claim_scope") in gr.SCOPES)
    print(f"[3] category={g.get('category')} confidence={g.get('confidence')} "
          f"scope={g.get('claim_scope')} valid={ok}")
    if g.get("asserted_objective"):
        print(f"[3] asserted: {g['asserted_objective']!r}")
    if g.get("reason_code", "").startswith("grader_"):
        print(f"[3] WARNING: grader problem -- {g.get('reason_code')}: "
              f"{str(g.get('brief_justification'))[:200]}")

    out = REPO / "results" / "pilot"
    out.mkdir(parents=True, exist_ok=True)
    dest = out / f"pilot_{a.arm}_{a.prompt}.json"
    dest.write_text(json.dumps({
        "_warning": "PILOT -- mechanical validation only. Excluded from all analysis.",
        "arm": a.arm, "prompt_variant": a.prompt,
        "agent_model": c.model, "grader_model": gr.GRADER_MODEL,
        "stop_reason": c.stop_reason,
        "input_tokens": c.input_tokens, "output_tokens": c.output_tokens,
        "cached_tokens": c.cached_tokens,
        "report": c.text, "grade": g,
    }, indent=2), encoding="utf-8")

    print(f"\n[4] wrote {dest}")
    print("\n--- report (first 1200 chars) ---")
    print(c.text[:1200])


if __name__ == "__main__":
    main()
