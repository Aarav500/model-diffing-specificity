# Positioning — paragraph one

Every factual assertion below is verified against primary text (see LITERATURE_VERIFICATION.md). The two
hedges — **"I could not find"** rather than "nobody has", and the explicit **not**-list — are what let this
survive being read by Nanda, Kassem, or Egler, any of whom may be the reviewer.

---

## Full version (write-up, S2)

> Model diffing and agentic auditing have recently acquired negative controls, but not the same one, and none
> of them yields a confabulation rate for a white-box auditor on a model pair that genuinely differs without
> having a hidden objective. Chughtai, Engels and Nanda (*Building and evaluating model diffing agents*, June
> 2026) run a diffing agent on identical model pairs under an explicit null-hypothesis scaffold and report
> that "the false positive rate in this setting [is] in general low" — but their auditor "is not shown target
> model thoughts, only outputs", so this is a black-box result. Kassem et al. (*Delta-Crosscoder*,
> arXiv:2603.04426) run one white-box null, on "two identical versions of LLaMA 3.1 8B Instruct that have not
> undergone any narrow or divergent finetuning"; because the method passes each input through both models,
> identical weights make the delta exactly zero by construction, so the test shows the pipeline does not
> hallucinate from nothing rather than that it stays silent on models that really differ — and their headline
> "0% method-level false positives" counts, by their own definition, a *failure to recover* a causal latent,
> which is a miss, computed over ten organisms that all have real objectives. Their blinded grader, the
> component that would actually confabulate, is never run on the null. Egler, Schulman and Carlini
> (arXiv:2510.16255) do report a genuine operating point against negative controls — 56.2% detection at a 1%
> false positive rate over 1400+ audits including five benign finetuned models — but for adversarial-finetuning
> safety degradation with dataset access, not open-ended hidden-objective attribution. Minder et al.'s
> Activation Difference Lens (arXiv:2510.13900) never runs its interpretability agent on a no-objective pair
> at all: its only near-null (Appendix E.1, base-vs-chat) is scored with the two low-level metrics only, and
> its rubric is undefined without a ground-truth objective — the authors had to feed the token-relevance
> grader "a generic description of chat-tuning" to make it runnable. AuditBench (arXiv:2602.22755) comprises
> 56 models *all* carrying implanted behaviors and reports recall only. What I could not find is a measurement
> of how often a white-box activation-diffing auditor names a specific hidden objective on a pair whose
> activations genuinely differ for benign reasons — a different seed, a nuisance finetune, a benign
> instruction-tune — where the delta is nonzero but the correct answer is "there is nothing here."
>
> This project is **not** the first null control in model diffing, **not** a claim that no auditing agent has
> ever reported a false-positive rate, and **not** a critique of ADL's positive results, which I reproduce as
> my positive control. It is an attempt to put a number on the specificity of the white-box pipeline in the
> regime where zero-delta nulls carry no information.

---

## Compressed version (application form, S1)

> Activation Difference Lens (Minder et al., arXiv:2510.13900) reports 91% of organisms detected at grade ≥2
> against a 39% black-box baseline. That is a sensitivity number. Its agent is never run on a pair with
> nothing to find, and its grader structurally cannot score one: in the released code
> (`science-of-finetuning/diffing-toolkit`), `hypothesis_grader.py` asserts that a ground-truth
> `description_long` exists, and all ten rubrics floor at "1: No valid information" — so an agent that
> correctly reports "these models don't differ" scores identically to one that hallucinated. Nulls do exist
> elsewhere, and I cite them: Chughtai, Engels & Nanda (June 2026) report a low FPR for a diffing agent on
> identical pairs, but black-box; Delta-Crosscoder runs a white-box null on byte-identical weights, where the
> delta is zero by construction; Egler et al. report 56.2% detection at 1% FPR, but for adversarial-finetuning
> detection with dataset access. Every existing null is either zero-delta or black-box. I measure the case
> none of them covers — a white-box auditor on a pair that genuinely differs for benign reasons — and report
> detection rate, false-positive rate, and abstention rate together, on a scale that can distinguish a correct
> abstention from a confident error.

---

## The three sentences that do the most work

1. *"`hypothesis_grader.py` asserts that a ground-truth `description_long` exists, so the agent can run on a
   null but the score cannot be produced."* — a structural claim, verifiable in 30 seconds by a reviewer, and
   it demonstrates the repo was read rather than the abstract.

2. *"All ten rubrics floor at 1: No valid information, so a correct abstention and a hallucination are
   numerically identical."* — reframes the contribution from "a missing experiment" to "a missing
   instrument", which is harder to scoop.

3. *"The agent's system prompt says: if the finetuned model is not answering differently than the base model,
   try to think of a question that would reveal the difference."* — the harness instructing the agent to keep
   hunting when it finds nothing. This is the mechanism, quoted from their own source.

---

## Framing discipline

- Say **"among the controls they run"**, never "their controls are". ADL runs ~11 controls, not 5.
- Say **91% / 39%**, never 97% / 12%. The latter is an appendix ablation of a weaker agent on a single run.
- Say ADL runs **"a mixing sweep, at which agent performance collapses by 1:1"**, never "one point at 1:1".
  There are twelve nonzero ratios in `run.sh`.
- Say Delta-Crosscoder's null has **"exactly zero signal by construction"**, not "cannot fail".
- Frame throughout as **measuring a rate nobody has measured**, never as an attack on ADL. ADL is the positive
  control; if it fails to reproduce, that is my bug, not their error.
