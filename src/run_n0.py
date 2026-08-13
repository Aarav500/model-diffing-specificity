"""Arm N0 at the artifact level: gemma-3-1b-pt vs gemma-3-1b-it.

This is the Phase 1 ramp deliverable (a base-vs-finetuned mean activation
difference computed by hand and decoded with logit lens) and simultaneously the
N0 diffing artifacts.

It does NOT produce a false-positive rate. That needs the agent, which needs
ANTHROPIC_API_KEY. This step produces only the evidence the agent would be shown.

Note on interpretation: ADL Appendix E.1 runs base-vs-chat pairs for Qwen3 1.7B,
Llama 3.2 1B and Llama 3.1 8B. Gemma-3-1B is in the repo's configs/organism/chat.yaml
but is not among the pairs reported in E.1.

  python -m src.run_n0 --n-texts 2000
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def fineweb_texts(n: int, min_chars: int = 400) -> list[str]:
    """Random web text -- the input distribution ADL uses."""
    from datasets import load_dataset
    ds = load_dataset(
        "HuggingFaceFW/fineweb", name="sample-10BT", split="train", streaming=True
    )
    out = []
    for ex in ds:
        t = ex["text"].strip()
        if len(t) >= min_chars:
            out.append(t)
        if len(out) >= n:
            break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="google/gemma-3-1b-pt")
    ap.add_argument("--ft", default="google/gemma-3-1b-it")
    ap.add_argument("--n-texts", type=int, default=2000)
    ap.add_argument("--n-positions", type=int, default=5)
    ap.add_argument("--out", type=Path, default=REPO / "results" / "artifacts" / "N0")
    ap.add_argument("--no-patchscope", action="store_true")
    a = ap.parse_args()

    from src.adl_core import run_diff

    print(f"Fetching {a.n_texts} FineWeb documents...")
    texts = fineweb_texts(a.n_texts)
    print(f"  got {len(texts)}")

    print(f"Diffing {a.ft} minus {a.base} over first {a.n_positions} positions...")
    path = run_diff(
        model_a_id=a.base,
        model_b_id=a.ft,
        texts=texts,
        out_dir=a.out,
        n_positions=a.n_positions,
        patchscope_layers=() if a.no_patchscope else (12, 18, 24),
    )
    print(f"Artifacts -> {path}")

    art = json.loads(path.read_text())
    norms = art["diff_norms_by_layer_position"]
    ranked = sorted(
        ((int(k.split("_")[1]), p, v) for k, vals in norms.items() for p, v in enumerate(vals)),
        key=lambda t: -t[2],
    )
    print("\nHighest-norm (layer, position) cells:")
    for l, p, v in ranked[:8]:
        print(f"  layer {l:>3} pos {p}: {v:10.2f}")

    print("\nLogit lens at the top cells:")
    top = {(l, p) for l, p, _ in ranked[:8]}
    for row in art["logit_lens_normed"]:
        if (row["layer"], row["position"]) in top:
            toks = ", ".join(repr(t) for t in row["tokens"][:12])
            print(f"  L{row['layer']:>3} p{row['position']}: {toks}")

    if art["patchscope_by_layer"]:
        print("\nPatchscope:")
        for layer, outs in art["patchscope_by_layer"].items():
            print(f"  layer {layer}:")
            for o in outs:
                print(f"    - {o!r}")


if __name__ == "__main__":
    main()
