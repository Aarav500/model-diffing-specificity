"""Compute diffing artifacts for any arm.

  # N1: base vs generic-FineWeb LoRA
  python -m src.run_arm --arm N1 --model-a google/gemma-3-1b-it --model-b results/models/N1/merged

  # N2: the two seeds against EACH OTHER, not against base
  python -m src.run_arm --arm N2 --model-a results/models/N2_seedA/merged \
                                 --model-b results/models/N2_seedB/merged

  # P: positive control
  python -m src.run_arm --arm P --model-a google/gemma-3-1b-it \
                               --model-b hcasademunt/gemma3_1b_it_cake_bake --adapter-b
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch

REPO = Path(__file__).resolve().parent.parent


def materialise_adapter(base_id: str, adapter_id: str, out: Path) -> str:
    """Merge a released LoRA adapter into its base and save, so the diffing path
    sees two plain causal LMs regardless of how the organism was distributed."""
    from peft import PeftModel
    from transformers import AutoTokenizer
    from src.adl_core import load_model, release

    if (out / "config.json").exists():
        print(f"  reusing merged adapter at {out}")
        return str(out)

    print(f"  merging {adapter_id} into {base_id} ...")
    base = load_model(base_id)
    merged = PeftModel.from_pretrained(base, adapter_id).merge_and_unload()
    out.mkdir(parents=True, exist_ok=True)
    merged.save_pretrained(out)
    AutoTokenizer.from_pretrained(base_id).save_pretrained(out)
    release(merged)
    return str(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True)
    ap.add_argument("--model-a", required=True)
    ap.add_argument("--model-b", required=True)
    ap.add_argument("--adapter-b", action="store_true",
                    help="model-b is a LoRA adapter to merge into model-a's base first")
    ap.add_argument("--tokenizer", default="google/gemma-3-1b-it")
    ap.add_argument("--n-texts", type=int, default=2000)
    ap.add_argument("--n-positions", type=int, default=5)
    ap.add_argument("--min-count", type=int, default=5)
    ap.add_argument("--no-patchscope", action="store_true")
    a = ap.parse_args()

    from transformers import AutoTokenizer
    from src.adl_core import (
        run_diff, load_model, logit_lens, corpus_token_frequencies,
        frequent_token_mask, release,
    )
    from src.run_n0 import fineweb_texts

    out_dir = REPO / "results" / "artifacts" / a.arm
    out_dir.mkdir(parents=True, exist_ok=True)

    model_b = a.model_b
    if a.adapter_b:
        model_b = materialise_adapter(a.model_a, a.model_b, out_dir / "_merged_b")

    print(f"Fetching {a.n_texts} FineWeb documents ...")
    texts = fineweb_texts(a.n_texts)

    print(f"[{a.arm}] diffing B={model_b}  minus  A={a.model_a}")
    path = run_diff(
        model_a_id=a.model_a,
        model_b_id=model_b,
        texts=texts,
        out_dir=out_dir,
        n_positions=a.n_positions,
        patchscope_layers=() if a.no_patchscope else (12, 18, 24),
    )

    # Frequent-token decode. Without this the logit lens is dominated by
    # effectively-untrained vocabulary (see results/N0_NOTES.md §2).
    tok = AutoTokenizer.from_pretrained(a.tokenizer)
    cache = out_dir / f"token_counts_{a.n_texts}.json"
    shared = REPO / "results" / "artifacts" / "N0" / f"token_counts_{a.n_texts}.json"
    if cache.exists():
        counts = {int(k): v for k, v in json.loads(cache.read_text()).items()}
    elif shared.exists():
        # Same tokenizer and same corpus -> same counts. Reuse rather than recount.
        counts = {int(k): v for k, v in json.loads(shared.read_text()).items()}
        cache.write_text(json.dumps({str(k): v for k, v in counts.items()}))
    else:
        counts = dict(corpus_token_frequencies(tok, texts))
        cache.write_text(json.dumps({str(k): v for k, v in counts.items()}))

    diff = torch.load(out_dir / "diff.pt")
    model = load_model(model_b)
    mask = frequent_token_mask(counts, model.lm_head.out_features, min_count=a.min_count)
    rows = logit_lens(diff, model, tok, top_k=20, allowed_mask=mask)
    release(model)

    art = json.loads(Path(path).read_text(encoding="utf-8"))
    art["logit_lens_frequent_only"] = [
        {"layer": r.layer, "position": r.position, "tokens": r.tokens, "logits": r.logits}
        for r in rows
    ]
    art["frequent_token_mask"] = {
        "min_count": a.min_count, "n_allowed": int(mask.sum()),
        "corpus": f"fineweb sample-10BT, {a.n_texts} docs",
    }
    Path(path).write_text(json.dumps(art, indent=2), encoding="utf-8")

    norms = art["diff_norms_by_layer_position"]
    flat = sorted(
        ((int(k.split("_")[1]), p, v) for k, vs in norms.items() for p, v in enumerate(vs)),
        key=lambda t: -t[2],
    )
    res = {(r.layer, r.position): r.tokens for r in rows}
    print(f"\n[{a.arm}] mean diff norm = "
          f"{sum(v for _, _, v in flat) / len(flat):.1f}")
    print(f"[{a.arm}] top cells excluding BOS (frequent-token decode):")
    for l, p, v in [t for t in flat if t[1] != 0][:6]:
        print(f"  L{l:>2} p{p} norm={v:9.1f}: " + " | ".join(res[(l, p)][:10]))
    print(f"[{a.arm}] at BOS:")
    for l, p, v in [t for t in flat if t[1] == 0][:3]:
        print(f"  L{l:>2} p0 norm={v:9.1f}: " + " | ".join(res[(l, p)][:10]))


if __name__ == "__main__":
    main()
