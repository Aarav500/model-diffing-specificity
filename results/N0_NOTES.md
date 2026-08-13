# N0 artifacts — `gemma-3-1b-pt` vs `gemma-3-1b-it`

**Run date:** 2026-08-12
**Status:** artifacts only. **This is not a false-positive rate.** The agent has not been run (no
`ANTHROPIC_API_KEY`). What follows is the evidence an agent *would* be shown, plus a methodological finding
about the decode.

**Config:** 2000 FineWeb `sample-10BT` documents, first 5 token positions, mean residual-stream difference
(`it` minus `pt`), 27 layers × 5 positions × 1152 dims, bf16 on an RTX 5060. Artifacts in
`results/artifacts/N0/`.

---

## 1. The difference is concentrated at the BOS position

| Position | Mean norm over layers | Max |
|---|---|---|
| 0 (BOS) | **20205** | 37267 |
| 1 | 4182 | 12588 |
| 2 | 4575 | 13858 |
| 3 | 4821 | 14650 |
| 4 | 4996 | 15371 |

Position 0 carries a difference 4–5× larger than any other. Since every sequence begins with the same `<bos>`
token, that component is **constant across all 2000 documents** — it is a property of the model pair, not of
the text. Any decode dominated by position 0 is reading a fixed offset, not a text-conditioned signal.

This matters for the agent evidence: if the highest-norm cells are selected by norm (as
`blind_harness.render_evidence` does), position 0 will crowd out everything else on every arm. Worth
pre-committing to reporting positions separately rather than pooling.

## 2. Naive logit lens fails — and the reason is identifiable

First decode, unrestricted over the full 262144-token vocabulary, positions 1–4:

```
L25 p4:  𒅜 | 𒐀 | 𒀺 | 𒌁 | 𒁖 | 𒍨 | 𒋆 | 𒍐 | 𒆦 | 𒆥
L25 p3:  𒅜 | 𒐀 | 𒌁 | 𒀺 | 𒋆 | 𒁼 | 𒍍 | 𒊝 | 𒆥 | 𒆦
```

Sumerian cuneiform (U+12000), `<unusedNNNN>` slots, and rare CJK. Not a semantic signal.

**Diagnosis:** an arbitrary direction in residual space projects onto the unembedding rows of *untrained*
tokens as readily as trained ones, and untrained rows are not organised into the structured subspace trained
ones occupy — so they win an unrestricted top-k. Measured directly: **only 16443 of 262144 tokens (6.3%)
appear at least 5 times in 2000 FineWeb documents.** The other 93.7% are near-init noise.

This is why ADL restricts token relevance to frequent tokens (`frequent_tokens_self`,
`token_relevance.py:284-330`). Found by reading the repo, not the paper.

## 3. With the frequent-token mask, real words appear

Same cells, restricted to the 16443 tokens with count ≥ 5:

```
L25 p4:  genuinely | herpes | Palin | TMZ | immigrant | Playboy | attered | astrolog | pastoral
L25 p3:  genuinely | herpes | attered | Palin | astrolog | immigrant | homosexual | straightforward
L25 p2:  herpes | attered | genuinely | astrolog | immigrant | straightforward | Playboy | Palin | homosexual
L24 p3:  Computation | File | Outcome | disparate | astrolog | tuna | genuinely | valid | flawed
```

At BOS (position 0):

```
L23 p0:  shy | skiing | snow | slavery | plastic | pins | shadows
L22 p0:  imaginable | snow | punches | hate | hated | destruction | joke | joking | applause | laughter
L21 p0:  hate | snow | joking | imaginable | joke | hated | kick | destruction | decrease | waking
```

## 4. What this does and does not show

**Does:** the hand-rolled ADL fallback (`src/adl_core.py`) works end to end on real models and real data, and
the frequent-token restriction is load-bearing rather than cosmetic. The Hour-5 kill-criteria fallback is
functional, which was its purpose.

**Does not:** produce anything resembling a coherent finetuning objective — which is the correct outcome for
N0, where the only difference is broad instruction-tuning and there is no narrow objective to find.

**A caution against myself.** Reading the position-2–4 tokens, my first reaction was "sensitive-topic /
safety-tuning directions" — `herpes`, `Playboy`, `homosexual`, `immigrant`, `Palin`, `slavery`, `hate`. That
is a plausible story and it may even be right. It is also **exactly the behaviour this study exists to
measure**, produced by a human who *knew in advance this was a null arm*. I am recording the impression rather
than acting on it, and it goes in the write-up as an anecdote, not a finding. It is a reason to trust the
blinding protocol over anyone's read of the artifacts, mine included.

## 5. Open questions for the real run

1. Should position 0 be excluded from the agent's evidence, reported separately, or left in? It dominates by
   norm but is text-independent. **Decide before running any arm, and record the decision in
   PREREGISTRATION.md §14** — deciding after seeing which choice produces a nicer FPR would invalidate the
   number.
2. `min_count` for the frequent-token mask is currently 5, chosen without tuning. It should be fixed across
   all arms and stated, not selected per arm.
3. Patchscope was skipped here (`--no-patchscope`) and has not been exercised on real data.
4. N0 is only one arm, and per PREREGISTRATION.md §2 it is a *descriptive* arm, not part of the headline FPR.
   N1 and N2 are the ones that matter, and neither has been built.
