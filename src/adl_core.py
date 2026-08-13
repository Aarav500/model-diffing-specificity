"""Hand-rolled Activation Difference Lens.

This is the Hour-5 fallback named in the sprint's kill criteria: if
`diffing-toolkit` has not produced an agent report by hour 5, this file replaces
it and every experimental arm survives unchanged.

The core signal from Minder et al. (arXiv:2510.13900) is simple: take the mean
residual-stream difference between a base and a finetuned model over the first
few token positions of random web text, then decode that difference with a logit
lens and with Patchscope. That is what this module implements, with no
dependency beyond `transformers` and `torch`.

Memory note: written for an 8GB card. Models are loaded and released one at a
time by default (`sequential=True`), so peak VRAM is one model plus a small
activation cache rather than two models at once.
"""

from __future__ import annotations

import gc
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, Sequence

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


# --------------------------------------------------------------------------
# Model plumbing
# --------------------------------------------------------------------------

def resolve_decoder(model):
    """Return (decoder_stack, final_norm, lm_head) across HF layouts.

    Gemma-3 text-only exposes `model.model.{layers,norm}`; the multimodal
    wrapper nests one level deeper under `language_model`. Llama/Qwen/Mistral
    all match the first case.
    """
    inner = model.model
    if hasattr(inner, "language_model") and hasattr(inner.language_model, "layers"):
        inner = inner.language_model
    if not hasattr(inner, "layers"):
        raise AttributeError(
            f"Could not locate decoder layers on {type(model).__name__}. "
            "Add an explicit case to resolve_decoder()."
        )
    return inner.layers, inner.norm, model.lm_head


def load_model(model_id: str, dtype=torch.bfloat16, device="cuda", **kw):
    # transformers v5 renamed torch_dtype -> dtype and warns on the old name.
    import transformers
    key = "dtype" if int(transformers.__version__.split(".")[0]) >= 5 else "torch_dtype"
    model = AutoModelForCausalLM.from_pretrained(
        model_id, device_map=device, **{key: dtype}, **kw
    )
    model.eval()
    return model


def release(model):
    del model
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


# --------------------------------------------------------------------------
# Activation collection
# --------------------------------------------------------------------------

@torch.no_grad()
def mean_activations(
    model,
    tokenizer,
    texts: Sequence[str],
    n_positions: int = 5,
    batch_size: int = 8,
) -> torch.Tensor:
    """Mean residual-stream activation at each (layer, position).

    Returns a tensor of shape (n_layers + 1, n_positions, d_model), float32 on
    CPU. Index 0 of the layer axis is the embedding output; index L is the
    output of decoder layer L.

    Because attention is causal, the activation at position i depends only on
    positions <= i. Truncating each text to exactly `n_positions` tokens
    therefore yields *identical* activations to running the full text and
    slicing -- so we truncate, which removes the need for padding and any
    attention-mask subtleties, and makes the pass cheap.
    """
    acc = None
    count = 0

    # Only the first `n_positions` tokens survive truncation, so slice the raw
    # strings first. Tokenizing a full multi-thousand-token web document to keep
    # five tokens dominates runtime otherwise. 40 chars/token is generous
    # headroom even for scripts that tokenize densely.
    max_chars = n_positions * 40

    for start in range(0, len(texts), batch_size):
        chunk = [t[:max_chars] for t in texts[start : start + batch_size]]
        enc = tokenizer(
            chunk,
            return_tensors="pt",
            truncation=True,
            max_length=n_positions,
            padding="max_length",
        )
        # Any sequence shorter than n_positions after truncation would introduce
        # pad tokens, which would contaminate the mean. Drop those rows.
        keep = enc["attention_mask"].sum(dim=1) == n_positions
        if not keep.any():
            continue
        input_ids = enc["input_ids"][keep].to(model.device)
        attn = enc["attention_mask"][keep].to(model.device)

        out = model(input_ids=input_ids, attention_mask=attn, output_hidden_states=True)
        # tuple of (n_layers+1) tensors, each (batch, n_positions, d_model)
        hs = torch.stack(out.hidden_states, dim=0).float()  # (L+1, B, P, D)
        batch_sum = hs.sum(dim=1).cpu()  # (L+1, P, D)

        acc = batch_sum if acc is None else acc + batch_sum
        count += input_ids.shape[0]

        del out, hs
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    if acc is None or count == 0:
        raise ValueError(
            f"No text reached {n_positions} tokens. Supply longer samples or "
            f"lower n_positions."
        )
    return acc / count


# --------------------------------------------------------------------------
# Decoding: logit lens
# --------------------------------------------------------------------------

@dataclass
class LensRow:
    layer: int
    position: int
    tokens: list[str]
    logits: list[float]


@torch.no_grad()
def corpus_token_frequencies(tokenizer, texts: Sequence[str], max_chars: int = 4000):
    """Token counts over a corpus, used to build the frequent-token mask.

    Rationale: an arbitrary direction in residual space projects onto the
    unembedding rows of *untrained* tokens as readily as trained ones, and
    untrained rows are not organised into the structured subspace the trained
    ones occupy -- so they dominate an unrestricted top-k. Gemma-3's 262k
    vocabulary contains large blocks of effectively-untrained tokens (cuneiform,
    <unusedNNNN>, rare CJK) which swamp the decode. ADL restricts token
    relevance to frequently-occurring tokens for this reason
    (`frequent_tokens_self`, token_relevance.py).
    """
    from collections import Counter
    counts = Counter()
    for t in texts:
        counts.update(tokenizer(t[:max_chars], add_special_tokens=False)["input_ids"])
    return counts


def frequent_token_mask(counts, vocab_size: int, min_count: int = 2) -> torch.Tensor:
    """Boolean mask over the vocabulary: True where the token is allowed."""
    mask = torch.zeros(vocab_size, dtype=torch.bool)
    for tok_id, c in counts.items():
        if c >= min_count and tok_id < vocab_size:
            mask[tok_id] = True
    return mask


@torch.no_grad()
def logit_lens(
    diff: torch.Tensor,
    model,
    tokenizer,
    top_k: int = 20,
    apply_final_norm: bool = True,
    allowed_mask: torch.Tensor | None = None,
) -> list[LensRow]:
    """Project an activation *difference* through the unembedding.

    `diff` is (n_layers+1, n_positions, d_model).

    On `apply_final_norm`: the final norm is RMSNorm, which is nonlinear, so
    applying it to a difference vector is not the same as differencing two
    normed vectors. Both conventions appear in the literature. The default
    applies the norm, because without it the scale of `diff` is arbitrary and
    the top-k ordering becomes dominated by whichever layer happens to have the
    largest raw norm. The flag exists so the choice can be reported, and both
    settings are logged in the artifacts the agent sees.
    """
    _, norm, lm_head = resolve_decoder(model)
    p = next(model.parameters())
    rows: list[LensRow] = []

    n_layers, n_pos, _ = diff.shape
    for layer in range(n_layers):
        for pos in range(n_pos):
            v = diff[layer, pos].to(device=p.device, dtype=p.dtype)
            v = norm(v.unsqueeze(0)) if apply_final_norm else v.unsqueeze(0)
            logits = lm_head(v).squeeze(0).float()
            if allowed_mask is not None:
                logits = logits.masked_fill(~allowed_mask.to(logits.device), float("-inf"))
            top = torch.topk(logits, k=top_k)
            rows.append(
                LensRow(
                    layer=layer,
                    position=pos,
                    tokens=[tokenizer.decode([i]) for i in top.indices.tolist()],
                    logits=[round(x, 4) for x in top.values.tolist()],
                )
            )
    return rows


# --------------------------------------------------------------------------
# Decoding: Patchscope
# --------------------------------------------------------------------------

PATCHSCOPE_PROMPT = "cat -> cat\n1135 -> 1135\nhello -> hello\n?"


@torch.no_grad()
def patchscope(
    vector: torch.Tensor,
    model,
    tokenizer,
    inject_layer: int = 2,
    max_new_tokens: int = 30,
    n_samples: int = 5,
    temperature: float = 1.0,
    scale: float = 1.0,
    prompt: str = PATCHSCOPE_PROMPT,
) -> list[str]:
    """Inject `vector` at the last token of an identity prompt and generate.

    The identity prompt trains the model in-context to echo whatever concept
    sits at the final position, so the continuation reads out what the injected
    direction encodes.
    """
    layers, _, _ = resolve_decoder(model)
    p = next(model.parameters())
    v = (vector.to(device=p.device, dtype=p.dtype) * scale)

    enc = tokenizer(prompt, return_tensors="pt").to(model.device)
    inject_pos = enc["input_ids"].shape[1] - 1

    def hook(_module, _args, output):
        # Decoder layers return a tuple; the residual stream is element 0.
        hidden = output[0] if isinstance(output, tuple) else output
        # Only patch the prompt pass, not subsequent single-token decode steps.
        if hidden.shape[1] > inject_pos:
            hidden[:, inject_pos, :] = v
        return (hidden,) + output[1:] if isinstance(output, tuple) else hidden

    handle = layers[inject_layer].register_forward_hook(hook)
    try:
        outs = []
        for i in range(n_samples):
            torch.manual_seed(i)
            gen = model.generate(
                **enc,
                max_new_tokens=max_new_tokens,
                do_sample=temperature > 0,
                temperature=temperature if temperature > 0 else None,
                top_p=0.95,
                pad_token_id=tokenizer.eos_token_id,
            )
            outs.append(tokenizer.decode(gen[0, enc["input_ids"].shape[1]:],
                                         skip_special_tokens=True).strip())
    finally:
        handle.remove()
    return outs


# --------------------------------------------------------------------------
# Top-level: run one arm
# --------------------------------------------------------------------------

def run_diff(
    model_a_id: str,
    model_b_id: str,
    texts: Sequence[str],
    out_dir: Path,
    n_positions: int = 5,
    top_k: int = 20,
    patchscope_layers: Iterable[int] = (8, 12, 16),
    sequential: bool = True,
    device: str = "cuda",
) -> Path:
    """Compute B - A activation differences and write decodable artifacts.

    Writes `artifacts.json` containing everything the auditing agent is allowed
    to see. Model identifiers are deliberately NOT written into that file -- the
    blinding protocol (PREREGISTRATION.md §3) requires the agent to see
    `model_a` / `model_b` and nothing more. Identifiers go to a sibling
    `provenance.json` which the agent never receives.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    tok = AutoTokenizer.from_pretrained(model_a_id)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    model_a = load_model(model_a_id, device=device)
    acts_a = mean_activations(model_a, tok, texts, n_positions=n_positions)
    if sequential:
        release(model_a)
        model_a = None

    model_b = load_model(model_b_id, device=device)
    acts_b = mean_activations(model_b, tok, texts, n_positions=n_positions)

    diff = acts_b - acts_a

    # Decode through the finetuned model's own head, as in ADL.
    lens_rows = logit_lens(diff, model_b, tok, top_k=top_k, apply_final_norm=True)
    lens_rows_raw = logit_lens(diff, model_b, tok, top_k=top_k, apply_final_norm=False)

    patch = {}
    for layer in patchscope_layers:
        if layer >= diff.shape[0]:
            continue
        # Patchscope reads the difference at the final collected position.
        patch[str(layer)] = patchscope(
            diff[layer, -1], model_b, tok, inject_layer=2, n_samples=5
        )

    norms = {
        f"layer_{l}": [round(diff[l, p].norm().item(), 4) for p in range(diff.shape[1])]
        for l in range(diff.shape[0])
    }

    artifacts = {
        "schema": "adl_core/v1",
        "n_texts": len(texts),
        "n_positions": n_positions,
        "n_layers": int(diff.shape[0]),
        "diff_norms_by_layer_position": norms,
        "logit_lens_normed": [asdict(r) for r in lens_rows],
        "logit_lens_unnormed": [asdict(r) for r in lens_rows_raw],
        "patchscope_by_layer": patch,
    }
    (out_dir / "artifacts.json").write_text(json.dumps(artifacts, indent=2))
    (out_dir / "provenance.json").write_text(
        json.dumps({"model_a": model_a_id, "model_b": model_b_id}, indent=2)
    )
    torch.save(diff, out_dir / "diff.pt")

    release(model_b)
    if model_a is not None:
        release(model_a)
    return out_dir / "artifacts.json"
