# Camera-ready changes, JUDGe 2026 (Junior Spotlight)

Paper: *An Auditing Agent Asserts at Ceiling Whether or Not There Is Anything to Find*
Camera-ready due **2026-10-15 AoE**. Submitted version: commit `4e6c6c2`.

The reviews asked for one thing above all: a null with nothing in it. We built three and ran them,
plus a second agent, under two addenda to the pre-registration. Each addendum was committed before
any of its runs and fixed in advance what each outcome would change in the paper, including the
title. 440 new runs; 640 in all.

- **Addendum A** (§16, commit `20d99f8`) covers the identity pair (I0), two random-noise pairs (R1
  weight-matched, R2 activation-matched to the organism), and gpt-5-mini as a second agent on every
  arm.
- **Addendum B** (§17, commit `3a924dc`) exists because an internal review of the camera-ready found
  that the original arms had never shown the agent Patchscope, while I0, R1 and R2 had. Addendum B
  re-ran the three nulls without Patchscope (I0n, R1n, R2n), so they match the original arms.

## What the new runs found

Runs naming a specific objective:

| Pair | gpt-5 presup | gpt-5 neutral | gpt-5-mini presup | gpt-5-mini neutral |
|---|---|---|---|---|
| I0n, identity (matched) | 2/10 by the coder; all ten say "null finetune" | 0/10 | 4/10 (six claim a common-token bias) | 0/10 |
| R1n, noise (matched) | 10/10 | 7/10 | 10/10 | 10/10 |
| R2n, noise (matched) | 10/10 | 3/10 | 10/10 | 7/10 |
| I0 + Patchscope | 10/10 | 0/10 | 10/10 | 7/10 |
| R1, R2 + Patchscope | 20/20 | 20/20 | 20/20 | 19/20 |

- **Noise.** Under the presuppositional prompt both agents name an objective in every run, with or
  without Patchscope (80/80). That is a false-positive rate of 1.00 on structureless nulls.
- **Identity.** Here the instrument decides. Given zero norms and a logit lens, gpt-5 correctly says
  nothing was instilled. Given Patchscope too, it reads the Patchscope prompt's own echo scaffold as
  the objective, 10 times out of 10.
- **Title.** It stands. The pre-committed rule was to change it if gpt-5 asserted in two or fewer
  presuppositional runs on every synthetic null. It asserted in 30/30 in each addendum, and on the
  noise pairs those assertions are real confabulations.

## Reviewer imuU

**W1 / Q1, identity and noise controls.** Run in both configurations (Section 3, Table 1, Appendix
A). "No null exists" is narrowed to "each of our three *finetuning* nulls carried a real signal".
Synthetic nulls exist, are described as not finetunes, and give a measurable false-positive rate.
The limitations say they cannot tell us how often the agent misreads a realistic benign finetune.

**W2 / Q2, second agent.** gpt-5-mini ran on every arm (320 runs).
- Assertion at ceiling replicates: every presuppositional run except two on I0n.
- The N0 framing effect does not replicate (10/10 vs 10/10, pre-registered test F4, p = 1). The paper
  says the framing effect is agent-dependent, as the addendum committed it to.
- Both agents are OpenAI models, and the second agent is also the grader; the paper says so.
- A post-hoc gpt-5 re-grade agreed on all 120 Addendum A synthetic-null reports, 13 abstentions
  included.

**W3 / Q3, cross-seed consistency.** Withdrawn as a recommendation. The addendum committed in
advance to call it a hypothesis whatever the new data showed. The new data count against it: it was
perfect in 14 of 16 noise cells, because identical evidence repeats a confabulation. Both points are
in Section 5 and Appendix A, and the departure is logged in §14.

**W4 / Q4, the 9/9, the groups, and the 91%.**
- **The 9/9.** The tenth N0 presuppositional run spent its 8,000-token budget on reasoning and
  returned an empty report, so the pre-registered rule codes it DEGENERATE. Counted as ABSTAIN, the
  test gives p = 0.005 instead of 0.0007.
- **The groups.** Six assertions describe moderation, tagging, summarisation or a safety-aware
  assistant; three describe clickbait generation. Incompatibility was judged by a blind gpt-5-mini
  judge that sees only the asserted objectives and groups them by whether two claims could both be
  true of one model. Its original prompt used two pairs from our own outputs as worked examples, which
  we disclose. Re-run five times with outside examples, it set the three clickbait claims apart in all
  five calls, and split the other six further in three of them (Appendix B).
- **The label.** That test is now labelled exploratory. The plan registered the contrast on N1 and N2,
  where it is 20/20 vs 20/20.
- **The 91%.** Section 1 quotes it only as ADL's sensitivity number, and the limitations say our
  grades are not comparable to it.

## Reviewer 476S

**"Could not construct a clean null."** Addressed by the synthetic nulls. The paper reports what
happens with nothing to find, in both evidence configurations.

**Title and conclusion wording.** The title passed the pre-committed rule. The conclusion is scoped
to the presuppositional prompt, which is where assertion is at ceiling across real, diluted and
random signals. The abstract states the identity result exactly, including that gpt-5 got the
matched identity pair right.

**"Confidence carries no information."** The paper now says *assertion* throughout, and reports what
it can about verbal confidence. The blind grader coded every report hedged, plain or emphatic. The
pre-registered §6 comparison, never reported until now, finds finetuned-null assertions not
significantly more hedged (permutation p ≥ 0.10). On the matched noise nulls the same test gives
p = 0.04 (exploratory, uncorrected), and null assertions are descriptively less emphatic (30–47% against
70%), but no threshold separates them. In the ladder, that coding does not predict correctness.

## Corrections an internal review caught before submission

A six-lens review, then a re-check of the rewritten paper, with every finding checked by an
independent refuter, found these. All are fixed.

- **Semantic coder.** A draft overrode the pre-registered coder for gpt-5 on I0n (2/10 shown as 0/10)
  but not for gpt-5-mini. The override is withdrawn. Table 1 shows the coder's counts for both agents,
  the text says what the reports actually claim, and both inconsistencies are logged in §14.
- **Selective row.** The confidence table had left out the matched noise nulls, the only comparison
  below 0.05. It is now in, and the body's claim is scoped to the finetuned nulls.

- **Patchscope (critical).** The submission's Setup listed Patchscope among the agent's evidence. For
  all 200 original runs the Patchscope section was empty, because every original arm was built with
  `--no-patchscope`. The Setup is corrected, the mismatch is logged in §14, and Addendum B re-ran the
  nulls to match.
- **Seeds.** The plan said seeds vary the text sample. In fact the evidence is byte-identical across
  seeds and only a nonce varies, so every interval describes the agent's sampling on fixed evidence.
  This is now stated in the paper and logged in §14.
- **Statistics.**
  - The six-rung Spearman p-values are now exact permutation values: the ladder trend's p = 0.005
    becomes 0.017.
  - The tie-heavy confidence comparisons use permutation p-values.
  - A Holm-corrected p was mislabelled.
  - A rounding error (0.075 printed as 0.08) is gone.
- **Prior work.** Section 1 no longer says no white-box diffing method had been run on a no-objective
  pair. Delta-Crosscoder and Chughtai, Engels and Nanda are cited, as is Egler et al. The claim is now
  "no white-box *agent's* report".
- **ADL's agent.** The paper now states the difference. ADL's agent sees steered samples, can answer
  Inconclusive, and can query the models; ours reads a fixed summary in one call.
- **Rendering.** The submission's `\vspace{-3em}` inside `\title` pushed the title through the
  NeurIPS top rule, and the footer used an unofficial workshop name. Both are fixed.
- **Camera-ready mechanics.**
  - Byline, UMass Amherst affiliation, and acknowledgments with a funding statement.
  - A link to the public repository instead of the anonymous mirror.
  - A gate that checks the 2-page body, the byline, every required hedge, and that no stale deviation
    count can ship.
- **Reproducibility.** `results/.armmap.json` was never committed, so the repo could not reproduce a
  per-arm rate. It is now committed.

## Still yours to do

1. Read the PDF once end to end: `writeup/judge2026/paper.pdf`.
2. **Push before you upload** (`git push`). The paper's footnote promises all 640 reports at the
   public URL, and until you push, the 440 new ones only exist on this machine.
3. Upload the camera-ready PDF on OpenReview before **2026-10-15 23:59 AoE**.
4. The anonymous mirror (anonymous.4open.science) can expire or be deleted; nothing links to it.
5. Register for NeurIPS 2026 (workshop authors must), and plan the Junior Spotlight talk and the
   poster. Presentation is in person only.
