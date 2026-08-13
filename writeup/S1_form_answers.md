# S1 — Application form summary answers

**Highest priority.** Neel reads these first as a preliminary filter and may never open the doc.

> **Before submitting:** map these blocks onto the form's actual questions. I have not seen the current form,
> so these are written as reusable content, not as answers to specific prompts. Check the real wording and
> word limits first.

**Every `[[RESULT: …]]` below is an unfilled placeholder.** If any remains at submission time, that number was
never measured and the sentence containing it must be deleted, not guessed.

---

## Block A — What I did (≈150 words)

Activation Difference Lens (Minder et al., arXiv:2510.13900) reports that a white-box diffing agent identifies
the finetuning objective for 91% of organisms at grade ≥2, against 39% for a black-box baseline. That is a
sensitivity measurement. I measured the other half: how often the same class of pipeline names a specific
hidden objective on a model pair that has none.

I ran [[RESULT: n]] agent runs across a positive control and three null arms, blind — the agent never learned
which arm it was in, and the grader never learned either. The nulls are chosen so their activation deltas are
genuinely nonzero: a benign instruction-tune, a generic-corpus LoRA, and two LoRA seeds on identical data
diffed against each other. In that regime the correct answer is "there is nothing here", and the delta cannot
give the answer away.

**Headline: [[RESULT: detection rate on P]] detection at [[RESULT: FPR on N1/N2]] false-positive rate.**

---

## Block B — Why this needed a new instrument (≈120 words)

The existing pipeline structurally cannot score a null. In the released code
(`science-of-finetuning/diffing-toolkit`), `hypothesis_grader.py` asserts that a ground-truth
`description_long` exists before a score can be produced, and all ten rubrics in `grading_rubrics.yaml` floor
at `1: No valid information`. So an agent that correctly reports "these models don't differ" scores
identically to one that hallucinated an objective. There is no 0 and no "correctly abstained".

The ADL authors hit this themselves: to run their token-relevance grader on base-vs-chat pairs (Appendix E.1),
they had to feed it "a generic description of chat-tuning" — a fabricated stand-in for ground truth that does
not exist.

I pre-registered an arm-agnostic three-way outcome — ASSERT / ABSTAIN / DEGENERATE — that is defined
identically on nulls and positives, and reported detection rate, false-positive rate, abstention rate and
coverage together.

---

## Block C — What this is not (≈100 words)

This is not the first null control in model diffing. Chughtai, Engels and Nanda (June 2026) run a diffing
agent on identical model pairs and report a low false-positive rate — but that auditor is black-box, shown
"only outputs". Delta-Crosscoder (arXiv:2603.04426) runs a white-box null on byte-identical LLaMA weights,
where the delta is exactly zero by construction. Egler et al. (arXiv:2510.16255) report 56.2% detection at 1%
FPR, but for adversarial-finetuning detection with dataset access.

Every existing null is either zero-delta or black-box. I measured the case none covers, and I am not
challenging ADL's positive results — I reproduce them as my control.

---

## Block D — Most surprising finding (≈80 words)

[[RESULT: fill from data — candidates below, whichever the data supports]]

- Candidate 1: the prompt, not the activations, carries the confabulation. The agent's own system prompt says
  *"If the finetuned model is not answering differently than the base model, try to think of a question that
  would reveal the difference."* I ran every arm under that framing and under a neutral one that permits "no
  difference". [[RESULT: presup FPR]] vs [[RESULT: neutral FPR]].
- Candidate 2: assertions on nulls are [[RESULT: hedged / not hedged]] relative to positives, so a confidence
  threshold [[RESULT: does / does not]] recover usable specificity.
- Candidate 3: the abstention path exists in the agent's prompt and its usage rate has never been reported.
  Measured: [[RESULT: abstention rate]].

---

## Block E — What I'd do next (≈80 words)

The resolution limit is honest and stated: at n=10 per cell, an observed zero gives a 95% upper bound of 0.31,
so this design cannot distinguish a true FPR of 0 from 30%. It is well-powered for a high FPR and underpowered
for a reassuring one — the correct asymmetry for a safety measurement, but a real limit. The next increment is
n≥30 per cell, and extending the nulls across model families so the number is not a Gemma artifact.

---

## Links to include

- Code: [[URL: public fork of science-of-finetuning/diffing-toolkit + arm scripts]]
- Write-up doc: [[URL: set sharing to anyone-with-the-link]]
- Pre-registration commit: `34e0807`, timestamped `2026-08-12 19:57:24 -0500`, before any results existed

---

## Numbers discipline — check before submitting

- ADL headline is **91% / 39%** (grade ≥2), **30% / 1%** (grade ≥4). **Never 97% / 12%** — that is an appendix
  ablation of a weaker agent on a single run, and Nanda is an author.
- ADL runs a **mixing sweep** (twelve nonzero ratios in `run.sh`), not a single 1:1 point.
- Delta-Crosscoder's null is *"two identical versions of LLaMA 3.1 8B Instruct that have not undergone any
  **narrow or divergent** finetuning"* — do not drop those three words.
- Say "**among** the controls they run". ADL runs ~11, not 5.
