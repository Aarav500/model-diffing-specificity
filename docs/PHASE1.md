# Phase 1 — Ramp

**Gate defined in the plan:** *"compute a base-vs-finetuned mean activation difference by hand, on any model
pair, and decode it with logit lens. When that works, Phase 1 is done."*

**Status: gate passed** — [results/N0_NOTES.md](../results/N0_NOTES.md), 2000 FineWeb documents,
`gemma-3-1b-it` minus `gemma-3-1b-pt`, decoded with logit lens. Gaps against the fuller ARENA syllabus are
recorded honestly in §4.

---

## 1. ARENA 1.2 competencies — hooks, caching, ablation

The plan's non-negotiable was *"you need to write a forward hook without help."* All three were implemented
from scratch in [src/adl_core.py](../src/adl_core.py) against raw `transformers`, **without TransformerLens**.
That is a harder path than the ARENA exercises (no `HookedTransformer`, no `run_with_cache`, no
`ActivationCache`), and it was necessary: TransformerLens has no Gemma-3 support in this stack, and the arms
need plain HF checkpoints anyway.

### Caching

`mean_activations()` collects the residual stream at every (layer, position) via `output_hidden_states=True`,
returning `(n_layers+1, n_positions, d_model)`.

One non-obvious property worth stating, because it is the difference between a slow implementation and a fast
one:

> Because attention is causal, the activation at position *i* depends only on positions ≤ *i*. Truncating each
> text to exactly `n_positions` tokens therefore yields **identical** activations to running the full text and
> slicing.

So the implementation truncates rather than slices — which removes padding entirely, removes any
attention-mask subtlety, and makes the pass cheap. Texts that fall short of `n_positions` after truncation are
dropped rather than padded, since pad tokens would contaminate the mean.

### Forward hooks

Written three times, for three different interventions. The Patchscope hook, which patches a vector into one
position of the prompt pass but must *not* fire on subsequent single-token decode steps:

```python
def hook(_module, _args, output):
    hidden = output[0] if isinstance(output, tuple) else output
    if hidden.shape[1] > inject_pos:          # prompt pass only, not decode steps
        hidden[:, inject_pos, :] = v
    return (hidden,) + output[1:] if isinstance(output, tuple) else hidden

handle = layers[inject_layer].register_forward_hook(hook)
try:
    ...
finally:
    handle.remove()                            # always, even on exception
```

Two details that bite: HF decoder layers return a **tuple** whose element 0 is the residual stream (so the
hook must reconstruct the tuple), and during `generate()` the hook fires once per decode step with
`seq_len == 1`, which is why the shape guard is there rather than an unconditional write.

### Ablation

`ablate()` performs standard directional ablation — project the direction out of the residual stream at every
position:

```python
d = direction / direction.norm()
def project_out(h):
    coeff = (h * d).sum(dim=-1, keepdim=True)
    return h - coeff * d                       # h <- h - (h · d̂) d̂
```

`steer()` is the additive counterpart (`h ← h + αv`) and implements ADL's second metric: if the activation
difference encodes the finetuning objective, steering the *base* model with it should push generations toward
that objective's domain.

## 2. Decoding — logit lens and Patchscope

`logit_lens()` projects a difference vector through the final norm and unembedding. One judgement call is
documented in the source rather than hidden:

> The final norm is RMSNorm, which is nonlinear, so applying it to a *difference* vector is not the same as
> differencing two normed vectors. Both conventions appear in the literature. The default applies the norm,
> because without it the scale of `diff` is arbitrary and the top-k ordering becomes dominated by whichever
> layer has the largest raw norm.

Both variants are computed and stored, so the choice is reportable rather than assumed.

**The result that mattered.** The first decode returned Sumerian cuneiform and `<unusedNNNN>` slots. Diagnosing
that produced the most useful thing learned in Phase 1: only **16443 of 262144 tokens (6.3%)** occur at least
5 times in 2000 FineWeb documents, and untrained unembedding rows are not organised into the structured
subspace trained ones occupy, so they win an unrestricted top-k. Restricting to frequent tokens recovers real
words. This is why ADL uses `frequent_tokens_self` — found by reading `token_relevance.py`, not the paper.

Full write-up: [results/N0_NOTES.md](../results/N0_NOTES.md).

## 3. Reading

All four papers read from full text including appendices, with adversarial cross-checking rather than a single
pass. Recorded in [LITERATURE_VERIFICATION.md](../LITERATURE_VERIFICATION.md).

The plan asked to *"know ADL's control section well enough to quote it."* That is satisfied — see §1 and §4 of
the verification doc, which enumerates all ~11 controls ADL runs, locates the single occurrence of the phrase
"false positive" in the paper (Appendix E.1), and quotes the grader-rubric floor from
`grading_rubrics.yaml`.

Reading also **refuted three claims** the project was built on, including the 97%/12% figure, which is an
appendix ablation of a weaker agent rather than the headline. Catching that before submission was worth more
than any exercise notebook.

## 4. Gaps — stated, not papered over

| Item | Status |
|---|---|
| ARENA 1.2 notebooks worked as exercises | **Not done.** Competencies demonstrated by implementation instead (§1). |
| TransformerLens | **Not used and not installed.** Raw HF hooks throughout; TL has no Gemma-3 support here. |
| ARENA 1.3.x — SAEs / probing | **Not done.** `sae_lens` not installed. |
| Attribution patching, circuit-level work | Not done; not needed for this project. |

The SAE gap is the real one. It does not block this project — ADL's core signal is the mean activation
difference, which needs no SAE — but it does limit how deeply I can engage with **Delta-Crosscoder**, whose
method is a BatchTopK crosscoder. I read that paper's claims and verified its null-test wording, but I could
not independently assess its architecture choices, and the write-up should not pretend otherwise.

## 5. What Phase 1 changed about the plan

1. The dilution ladder needs **no training** — `mix1-0p1` … `mix1-2p0` already exist as released adapters.
2. Gemma-3-1B organisms **are** available (`hcasademunt/gemma3_1b_it_cake_bake`,
   `stewy33/gemma-3-1b-it-…-cake_bake-f84276e4`), so arm P fits an 8GB card.
3. N1's hyperparameters are now **copied, not guessed**: r=64, α=128, all seven projections, lr 1e-5, linear,
   1 epoch, seed 42 — from the organisms' own `adapter_config.json` and `train_config.json`.
4. The frequent-token mask is **load-bearing**, not cosmetic. Any arm decoded without it produces noise.
