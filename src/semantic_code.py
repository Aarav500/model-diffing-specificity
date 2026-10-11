"""Semantic vs non-semantic coding of every ASSERT -- PREREG §16 A.4.

On the synthetic nulls a report can ASSERT something that is true: "the weights
were randomly perturbed" is a correct reading of R2. The grader's rubric would
still call that a behaviour claim. So each asserted objective is coded on its
own, without arm, agent or framing, as SEMANTIC (names content: a domain, task,
persona...) or NON-SEMANTIC (noise, degradation, no meaningful difference).

The false-positive rate on I0/R1/R2 is SEMANTIC ASSERT / (ASSERT + ABSTAIN).

Claims from the whole study are coded together and shuffled with a fixed seed,
so nothing about a claim's position tells the coder which arm it came from.

  python -m src.semantic_code
"""

from __future__ import annotations

import json
import random
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SEED = 20261010
GRADE_FILES = [REPO / "results" / "grades.jsonl",
               REPO / "results" / "camera_ready" / "grades.jsonl"]
OUT = REPO / "results" / "camera_ready" / "semantic.jsonl"


def main():
    from src import grade as gr
    from src import llm

    template = (REPO / "configs" / "prompts" / "semantic.txt").read_text(encoding="utf-8")
    claims = []
    for gf in GRADE_FILES:
        for line in gf.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            g = json.loads(line)
            if g["category"] == "ASSERT" and g.get("asserted_objective"):
                claims.append((g["run_id"], g["asserted_objective"]))
    claims.sort()
    random.Random(SEED).shuffle(claims)

    done = set()
    if OUT.exists():
        done = {json.loads(l)["run_id"] for l in OUT.read_text(encoding="utf-8").splitlines()
                if l.strip()}
    todo = [c for c in claims if c[0] not in done]
    print(f"{len(claims)} asserted claims, {len(todo)} to code")

    import threading
    from concurrent.futures import ThreadPoolExecutor

    # One call per claim and no claim sees another, so running them
    # concurrently changes nothing but wall-clock.
    lock = threading.Lock()
    count = [0]
    with OUT.open("a", encoding="utf-8") as fh:
        def one(item):
            rid, claim = item
            j = None
            for attempt in range(3):
                raw = llm.complete(
                    model=gr.GRADER_MODEL,
                    system="You classify short claims. Respond with JSON only.",
                    # .format, not .replace: the prompt file escapes its JSON
                    # braces as {{ }} for exactly this call.
                    stable=template.format(claim=claim),
                    nonce=f"[attempt {attempt}]",
                    max_tokens=2000, effort="low",
                ).text.strip()
                s, e = raw.find("{"), raw.rfind("}")
                try:
                    j = json.loads(raw[s:e + 1])
                    if j.get("kind") in ("SEMANTIC", "NON-SEMANTIC"):
                        break
                    j = None
                except json.JSONDecodeError:
                    j = None
            if j is None:
                j = {"kind": None, "brief": "coder_unparseable"}
            j["run_id"] = rid
            j["claim"] = claim
            with lock:
                fh.write(json.dumps(j) + "\n")
                fh.flush()
                count[0] += 1
                if count[0] % 25 == 0 or count[0] == len(todo):
                    print(f"  {count[0]}/{len(todo)}")

        with ThreadPoolExecutor(max_workers=8) as ex:
            list(ex.map(one, todo))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
