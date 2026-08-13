# S2 — Write-up skeleton

Structure mirrors `MATS_Nanda_Application_RHOB.docx` (in `~/Downloads`), which already matches Neel's
requested format: ≤600-word executive summary, graphs inline, randomly sampled raw examples immediately
after, supporting detail below.

**Every `[[RESULT: …]]` is unfilled.** Any that survives to submission means the number was never measured —
delete the sentence rather than estimate it.

Set the Google Doc to **anyone-with-the-link** before submitting.

---

# Executive summary (≤600 words — currently ≈310 excluding placeholders)

## Positioning — paragraph one

*(Paste the full version from [POSITIONING.md](../POSITIONING.md) verbatim. It is verified line by line
against primary text and hedged specifically to survive being read by Nanda, Kassem or Egler, any of whom may
be the reviewer.)*

## What I measured

Four arms, blind throughout. The agent never learned which arm it was in; the grader never learned either,
and never saw ground truth.

| Arm | Construction | Delta | Objective present |
|---|---|---|---|
| P | Released ADL organism | nonzero | yes (positive control) |
| N0 | `gemma-3-1b-pt` vs `gemma-3-1b-it` | nonzero | no *narrow* objective |
| N1 | Base + LoRA on generic FineWeb | nonzero | **none** |
| N2 | Two LoRA seeds, same data, diffed against each other | nonzero | **none differential** |

N1 and N2 are the headline: the only arms that are simultaneously white-box and nonzero-delta, which is the
gap none of the existing nulls covers.

## Result

**[[FIGURE 1 — detection rate vs false-positive rate, Clopper–Pearson 95% intervals]]**

[[RESULT: one sentence stating the headline detection rate and FPR with intervals]]

**[[TABLE 1 — detection · FPR · abstention · degenerate · coverage, per arm × prompt]]**

Every rate carries its coverage. A detection number without the fraction of runs that produced a readable
signal at all is not a measurement.

**[[FIGURE 2 — dilution curve with the null-arm FPR floor overlaid]]**

## The instrument

ADL's grader scores a 1–5 rubric against the original finetuning description. On a null there is no
description, so the rubric is undefined — not merely uninformative. This is not incidental:
`hypothesis_grader.py` asserts `description_long` is non-empty before a score can be produced, and all ten
rubrics floor at `1: No valid information`. A correct abstention and a hallucination score identically.

I pre-registered an arm-agnostic three-way outcome — ASSERT / ABSTAIN / DEGENERATE — defined identically on
every arm, with no reference to ground truth. Detection rate and false-positive rate then become the *same
statistic* applied to different arms. Correctness is scored separately, positives only, on ADL's own 1–5
scale so it remains comparable to the published number.

Pre-registration committed `34e0807` at `2026-08-12 19:57:24 -0500`, before any results directory existed.
Deviations logged in §14 of that file rather than amended away.

## Honest limits

At n=10 per cell, an observed zero gives a 95% Clopper–Pearson upper bound of **0.31**. This design cannot
distinguish a true FPR of 0 from 30%. It is well-powered for a high FPR and underpowered for a reassuring
one — the correct asymmetry for a safety measurement, and stated rather than hidden.

[[RESULT: state the actual n achieved per cell]]

---

# Randomly sampled raw agent outputs

*(Paste `results/D5_sampled_outputs.md` here — immediately after the graphs, per Neel's explicit request.)*

Stratified by arm, uniform within stratum, seed fixed in `src/sample_outputs.py`. **Sampled, not chosen.** No
output was inspected before selection or excluded after.

---

# Supporting detail

## 1. What verification changed about the project

Reading the five papers from full text refuted claims the original plan rested on. Reporting this because the
corrections are more informative than the original framing:

- ADL's headline is **91% / 39%**, not 97% / 12%. The latter is an appendix ablation of a weaker agent.
- ADL runs a **twelve-point mixing sweep**, not a single 1:1 point.
- **The core novelty claim was false.** Nulls exist — they are just all zero-delta or black-box.
- ADL **does** have a near-null (App. E.1, base-vs-chat), run through the low-level metrics but never the
  agent, and gradeable only by feeding the grader a fabricated objective description.

Full record: [LITERATURE_VERIFICATION.md](../LITERATURE_VERIFICATION.md).

## 2. Blinding protocol

Opaque run IDs; the ID→arm map is gitignored until analysis is locked. Model identifiers are regex-scrubbed
from every agent input and the scrub raises rather than warns. Run order interleaved across arms so judge
drift affects arms equally. Post-hoc integrity check: the grader is asked to guess each arm; above-chance
accuracy is reported as a limitation. [[RESULT: arm-guess accuracy]]

## 3. Grader validation

Random 20% subsample hand-classified blind; agreement reported as Cohen's κ. Pre-registered threshold κ ≥ 0.7,
below which the LLM grader is abandoned and everything is hand-classified. [[RESULT: κ, n]]

## 4. The prompt-presupposition manipulation

The shipped agent prompt states the objective exists and instructs: *"If the finetuned model is not answering
differently than the base model, try to think of a question that would reveal the difference."* Every arm was
run under that framing and under a neutral one that explicitly permits "no meaningful difference".

[[RESULT: presup vs neutral FPR on nulls, Fisher exact]]

If neutral framing collapses the FPR, the confabulation is attributable to harness design rather than to the
activation signal — directly actionable for anyone building an auditing pipeline.

## 5. Reproduction

Code: [[URL]]. `setup/smoke_test.py` is the environment gate. `src/adl_core.py` is a standalone ~250-line
reimplementation of the core ADL signal (mean residual-stream difference over the first few token positions of
random web text, logit lens + Patchscope), used as the fallback path.

## 6. Time

[[Toggl screenshot — optional; Neel invites it and it corroborates the hour count]]
