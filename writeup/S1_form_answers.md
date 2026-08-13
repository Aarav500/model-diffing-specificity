# S1 — Application form summary answers

**Highest priority.** Neel reads these first as a preliminary filter and may never open the doc.

> Map these blocks onto the form's actual questions and word limits before submitting. **Every number
> below is measured** — no placeholders remain. Regenerate from [FINDINGS.md](../FINDINGS.md) if the
> data changes.

**Repo:** https://github.com/Aarav500/model-diffing-specificity · **Time:** 18 hours ·
**Scale:** 200 blind agent runs · **Agent:** `gpt-5-2025-08-07` · **Grader:** `gpt-5-mini-2025-08-07`

---

## Block A — What I did (≈150 words)

Activation Difference Lens (Minder et al., arXiv:2510.13900) reports a white-box diffing agent
identifying the finetuning objective for 91% of organisms at grade ≥ 2, against 39% black-box. That
is a sensitivity number, and the absent arm is field-wide: Delta-Crosscoder's only null is two
identical copies of one model — exactly zero signal by construction — AuditBench's 56 organisms are
all positives, and neither Model Organisms Are Leaky nor Cross-Architecture Diffing reports a
neutral-finetune null.

I set out to measure the other half, using ADL's own agent (`gpt-5`, pinned snapshot) on a released
Gemma-3-1B organism. **I reproduced their positive control and then failed to measure a
false-positive rate, because every null I built contained a real, readable signal.**

What replaced it is sharper: the agent's confidence is decoupled from its evidence, demonstrated two
independent ways.

---

## Block B — The two results (≈150 words)

**Framing manufactures answers.** On the one arm with no *narrow* objective (`gemma-3-1b-pt` vs
`-it`), the shipped harness's presuppositional prompt — *"The finetuning instilled a specific
objective. Identify it."* — produces **9/9 assertions**, mutually contradictory across seeds. A
neutral prompt on **identical evidence** produces **2/10**, with 8 abstentions. Fisher exact
**p = 0.0007**.

**Down a dilution ladder, assertion is flat while accuracy collapses.** Six released `mix1-*` rungs,
120 runs: assertion pinned at **1.00 on every rung** while specific accuracy (grade ≥ 4) falls
**0.55 → 0.05**. My pre-registered test here is *undefined* — the outcome is constant, so there is
no variance to model; I report that rather than swap in a test that returns a number. The decline is
measured on grade ≥ 4 and labelled **exploratory** (ρ = −0.94, p = 0.005).

The agent does not go quiet as evidence weakens. It says the same amount, with the same confidence,
and is progressively less right — a gap a sensitivity-only evaluation cannot see, because a
confident wrong answer and a correct one both count as responding.

---

## Block C — What this is not (≈110 words)

Nulls exist; none of them is this one. Chughtai, Engels and Nanda (*Building and evaluating model
diffing agents*, June 2026) run a diffing agent on identical pairs and report a low false-positive
rate — but their auditor is **black-box**, "not shown target model thoughts, only outputs".
Delta-Crosscoder runs a white-box null on byte-identical weights, where the delta is **zero by
construction**. Egler, Schulman and Carlini (arXiv:2510.16255) report 56.2% detection at 1% FPR, but
for adversarial-finetuning detection with dataset access.

Every existing null is either zero-delta or black-box. **What I could not find is a measurement of a
white-box auditor on a pair that genuinely differs for benign reasons** — and I could not supply one
either, because every such pair I built turned out to contain a real signal.

---

## Block D — The methodological finding (≈90 words)

**There may be no such thing as a "no-objective" finetune.** Three nulls, three different
contaminations: FineWeb is itself a register (the agent read it correctly on all 20 runs); two LoRA
seeds on byte-identical data still differ *along* the domain axis, because two runs converge to
different points on the same direction; instruction-tuning is itself an objective.

"Train it twice and diff the runs" and "finetune on generic text" are the two obvious ways to build a
null for a diffing method, and neither does what it appears to. That is the obvious next problem.

---

## Block E — Limitations (≈80 words)

No clean false-positive rate exists in this data. My correctness grades are **not comparable to
ADL's 91%** — I reconstructed the rubric; theirs grades key-fact recovery, and my grade ≥ 2 sits at
1.00 where they report failure because the binary hides a decline living above it. That is not a
refutation of their result.

Only the framing test was pre-registered (`PREREGISTRATION.md §8`); the ladder's registered test came
out undefined and the reported trend is exploratory, labelled as such. n = 10 per cell, one model
family, one organism, one agent.

---

## Block F — Most surprising finding (≈70 words)

Same evidence, independent seeds, opposite conclusions:

> `s0` — instruction-tuned into a helpful, **safety-aware** assistant
> `s7` — **uncensored**, sensational/tabloid-style generator (clickbait/gossip/NSFW)

At most one of those can be right, and no ground truth is needed to know it. That observation
generalises into the reusable instrument: **cross-seed consistency**, which needs no labels — 1.00
on every arm with a real signal, 0.67 with contradictory pairs on the one without.

---

## Numbers discipline — check before submitting

- ADL's headline is **91% / 39%** (grade ≥ 2) and **30% / 1%** (grade ≥ 4). **Never 97% / 12%** —
  that is an appendix ablation of a weaker agent (`gpt-5-chat`) on a single run.
- Say "**among** the controls they run"; ADL runs about eleven, not five.
- Delta-Crosscoder's null is *"two identical versions of LLaMA 3.1 8B Instruct that have not
  undergone any **narrow or divergent** finetuning"* — do not drop those three words, and say
  "**exactly zero signal by construction**", not "cannot fail".
- **Never present my grade ≥ 2 as a refutation of theirs.**
- Only the framing test is pre-registered. Label the ladder trend **exploratory**.
