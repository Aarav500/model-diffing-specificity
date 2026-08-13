# Artifact-level comparison across arms

**Date:** 2026-08-12
**Status:** diffing artifacts only. **No agent has been run on N1, N2 or P**, so
nothing here is a detection rate or a false-positive rate. This records what the
*evidence* looks like before any agent sees it.

All arms: 2000 FineWeb documents, first 5 token positions, frequent-token decode
(min_count 5, 16443 of 262144 tokens allowed).

---

## 1. Difference magnitude spans three orders of magnitude

| Arm | Construction | Mean diff norm |
|---|---|---|
| **N0** | `gemma-3-1b-pt` → `gemma-3-1b-it` | **~8194** |
| **N1** | base + LoRA on generic FineWeb | **486.6** |
| **N2** | LoRA seed B − LoRA seed A, identical narrow data | **17.7** |

N2's delta is **28× smaller than N1** and **~460× smaller than N0**. It is
nonzero — unlike Delta-Crosscoder's identical-weights null — but it is faint.

## 2. N1 is a clean null. N2 is not.

**N1** (generic-corpus LoRA, hyperparameters copied from the organism) decodes
to no coherent theme at all:

```
L25 p1:  Lane | Hand | TV | Than | - | ( | No | Break | Radio | May
L24 p1:  TV | - | Hand | Ads | ( | subscribers | ads | Lane | Safety | May
L25 p0:  Touch | Weller | Linda | chairman | Michele | Space | cadmium | Radiation
```

Generic web-text residue. A real, nonzero, matched finetune with nothing to
find. **This is what the arm was designed to be.**

**N2** — two LoRA runs on *identical* `cake_bake` data, differing only in
training seed — decodes to the domain, unmistakably:

```
L23 p1:  Bake | Cooking | Baked | Chef | baking | Cook | Kitchen | kitchen | culinary
L21 p1:  Cooking | Cook | Bake | baking | Baked | kitchen | Chef | recipes | bake
L25 p0:  cake | Cake | cakes | cake | removable | professionalism | vanilla
```

### Why this happens, and why it was not obvious in advance

Both N2 models were trained on the same corpus with the same hyperparameters and
the same data order (`data_seed` was held fixed precisely so only optimisation
randomness would vary). The expectation was that B − A would be *orthogonal* to
the domain: shared content cancels, leaving only seed noise.

It does not cancel. Two runs converge to different points **along the same
domain direction**, so the residual B − A still points along that direction. A
seed difference is a difference in *how far* each run travelled toward the
domain, not a difference in *which way* it went.

**This is a reportable methodological result in its own right.** The
null-construction space for model diffing now looks like:

| Null | Delta | Domain-aligned? | Clean? |
|---|---|---|---|
| Identical weights (Delta-Crosscoder) | exactly zero | n/a | Cannot fail — no signal to misread |
| **Seed difference (N2)** | **nonzero but faint** | **yes** | **No — carries the domain** |
| **Matched nuisance finetune (N1)** | **nonzero** | **no** | **Yes** |

Nobody appears to have reported that seed-difference nulls are domain-contaminated.
It is worth stating, because "train it twice and diff the runs" is the obvious
first idea for building a null and it does not do what it looks like it does.

## 3. Consequences for the analysis — decided before any agent run

1. **N1 carries the headline false-positive rate.** It is the only arm that is
   simultaneously white-box, nonzero-delta, and domain-free. PREREGISTRATION.md
   §2 named N1 and N2 jointly as the headline; on this evidence the weight moves
   to N1, and the reason is recorded here rather than discovered later.

2. **N2 remains interpretable, via a rule fixed in advance.** PREREGISTRATION.md
   §4 already requires the blind grader to record `claim_scope` (difference vs
   shared) and mechanically recounts a `shared` ASSERT as ABSTAIN on N2. That
   rule was written for exactly this case: an agent that says *"both models look
   baking-tuned"* is **correct**, and only *"model B was tuned for baking and
   model A was not"* is a false positive. The rule is unchanged — this evidence
   is why it exists.

3. **N2 may land in the coverage column rather than the rate column.** At mean
   norm 17.7 the signal may be too faint for the agent to say anything at all.
   If so that is a DEGENERATE/ABSTAIN result and belongs in the coverage figure
   (PREREGISTRATION.md §4), not in the FPR numerator or denominator.

## 4. What is still unmeasured

Everything that matters. No agent has run on N1, N2 or P. Detection rate, FPR,
abstention rate and coverage are all still unknown, and nothing above licenses a
guess about them — a legible artifact does not imply the agent reads it correctly,
and a faint one does not imply the agent stays silent.
