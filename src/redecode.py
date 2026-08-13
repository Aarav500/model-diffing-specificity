"""Re-decode a saved diff.pt with the frequent-token mask, without recomputing
activations.

The first N0 decode was dominated by effectively-untrained vocabulary (cuneiform,
<unusedNNNN>, rare CJK). This applies the frequent-token restriction ADL uses and
reports both decodes side by side, so the effect of the mask is visible rather
than assumed.

  python -m src.redecode --arm N0 --n-texts 2000
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import torch
from transformers import AutoTokenizer

REPO = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="N0")
    ap.add_argument("--decode-model", default="google/gemma-3-1b-it")
    ap.add_argument("--n-texts", type=int, default=2000)
    ap.add_argument("--min-count", type=int, default=5)
    ap.add_argument("--top-k", type=int, default=20)
    a = ap.parse_args()

    from src.adl_core import (
        load_model, logit_lens, corpus_token_frequencies, frequent_token_mask,
    )
    from src.run_n0 import fineweb_texts

    art_dir = REPO / "results" / "artifacts" / a.arm
    diff = torch.load(art_dir / "diff.pt")
    print(f"loaded diff {tuple(diff.shape)} from {art_dir}")

    tok = AutoTokenizer.from_pretrained(a.decode_model)

    cache = art_dir / f"token_counts_{a.n_texts}.json"
    if cache.exists():
        counts = {int(k): v for k, v in json.loads(cache.read_text()).items()}
        print(f"loaded cached token counts ({len(counts)} distinct)")
    else:
        print(f"counting token frequencies over {a.n_texts} FineWeb docs...")
        counts = dict(corpus_token_frequencies(tok, fineweb_texts(a.n_texts)))
        cache.write_text(json.dumps({str(k): v for k, v in counts.items()}))

    model = load_model(a.decode_model)
    # Size the mask to the unembedding, not the tokenizer: Gemma-3's tokenizer
    # reports 262145 while lm_head emits 262144.
    vocab = model.lm_head.out_features
    mask = frequent_token_mask(counts, vocab, min_count=a.min_count)
    print(f"  vocab={vocab}  allowed={int(mask.sum())} "
          f"({100*int(mask.sum())/vocab:.1f}%)  min_count={a.min_count}")
    rows = logit_lens(diff, model, tok, top_k=a.top_k, allowed_mask=mask)

    art_p = art_dir / "artifacts.json"
    art = json.loads(art_p.read_text(encoding="utf-8"))
    art["logit_lens_frequent_only"] = [
        {"layer": r.layer, "position": r.position, "tokens": r.tokens, "logits": r.logits}
        for r in rows
    ]
    art["frequent_token_mask"] = {
        "min_count": a.min_count, "n_allowed": int(mask.sum()), "vocab_size": vocab,
        "corpus": f"fineweb sample-10BT, {a.n_texts} docs",
    }
    art_p.write_text(json.dumps(art, indent=2), encoding="utf-8")

    norms = art["diff_norms_by_layer_position"]
    flat = sorted(
        ((int(k.split("_")[1]), p, v) for k, vs in norms.items() for p, v in enumerate(vs)),
        key=lambda t: -t[2],
    )
    unres = {(r["layer"], r["position"]): r["tokens"] for r in art["logit_lens_normed"]}
    res = {(r.layer, r.position): r.tokens for r in rows}

    print("\n=== unrestricted vs frequent-token-only, top cells excluding BOS ===")
    for l, p, v in [t for t in flat if t[1] != 0][:6]:
        print(f"\nL{l} p{p}  norm={v:.0f}")
        print("  all vocab :", " | ".join(unres[(l, p)][:10]))
        print("  frequent  :", " | ".join(res[(l, p)][:10]))

    print("\n=== frequent-token decode at BOS (position 0) ===")
    for l, p, v in [t for t in flat if t[1] == 0][:4]:
        print(f"  L{l} p0 norm={v:.0f}: " + " | ".join(res[(l, p)][:10]))


if __name__ == "__main__":
    main()
