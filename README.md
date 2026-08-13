# What does a model-diffing agent say about a model with nothing to find?

Measuring the **specificity** of a white-box activation-diffing auditor: how often it names a specific hidden
objective on a model pair that genuinely differs but has no objective to find.

MATS sprint, Neel Nanda stream. Deadline 2026-09-04.

---

## Status — 2026-08-12

Honest accounting. **No experimental arm has been run and no result exists.**

### Complete

| # | Deliverable | State |
|---|---|---|
| — | **Literature verification** | [LITERATURE_VERIFICATION.md](LITERATURE_VERIFICATION.md) — 5 papers read from full text, 2 load-bearing claims adversarially tested, repo read at `e0b84a5` |
| — | **Positioning** | [POSITIONING.md](POSITIONING.md) — paragraph one, both long and form-length |
| **D4** | **Pre-registered rubric** | [PREREGISTRATION.md](PREREGISTRATION.md) — committed `34e0807`, `2026-08-12 19:57:24 -0500`, before any `results/` existed |
| **D6** | **Code** | `src/` — hand-rolled ADL, blinding harness, grader, LoRA arms, analysis, D5 sampler |
| — | **Phase 0 environment** | Python 3.12.13 venv, torch 2.13.0+cu130 on RTX 5060 (sm_120), transformers 5.15, HF authenticated |

### Not done — and why

| # | Deliverable | Blocker |
|---|---|---|
| **D1** | Figure 1 — detection vs FPR | Requires running the arms. `src/analyze.py` produces it from real grades and **refuses to run without them**. |
| **D2** | Figure 2 — dilution curve | Same. |
| **D3** | Table 1 | Same. |
| **D5** | Sampled agent outputs | Same. `src/sample_outputs.py` exits rather than fabricate examples. |
| **S1/S2** | Form answers, write-up | Structure ready in `writeup/`; every number is a `[[RESULT]]` placeholder. |

These four are **measurements**. Producing them without running the models would be fabricated data in a study
whose entire thesis is that people report detection rates without measuring error rates.

**Immediate blocker:** `ANTHROPIC_API_KEY` is not set. The agent and grader both need it.

```bash
$env:ANTHROPIC_API_KEY = "sk-ant-..."
```

---

## What verification changed

Reading the primary sources refuted several claims the plan rested on. Full detail in
[LITERATURE_VERIFICATION.md](LITERATURE_VERIFICATION.md); the three that matter most:

1. **ADL's headline is 91% vs 39%, not 97% vs 12%.** The latter is an appendix ablation of a weaker agent on a
   single run. Nanda is an author — this error would have been caught instantly.
2. **The core novelty claim was false.** Nulls exist: Chughtai/Engels/Nanda (June 2026, black-box),
   Delta-Crosscoder (white-box but zero-delta), Egler et al. (56.2% detection @ 1% FPR, black-box). What
   survives — and what arms N1/N2 were always designed for — is the **nonzero-delta white-box** case that none
   of them covers.
3. **The pipeline structurally cannot score a null.** `hypothesis_grader.py` asserts a ground-truth
   `description_long` exists; all ten rubrics floor at `1: No valid information`. A correct abstention and a
   hallucination score identically. This turns the contribution from "a missing experiment" into "a missing
   instrument", which is harder to scoop.

It also found the agent's own system prompt says: *"If the finetuned model is not answering differently than
the base model, try to think of a question that would reveal the difference."* The harness instructs the agent
to keep hunting when it finds nothing — which is why `presup` vs `neutral` is pre-registered as a manipulation
rather than added later as an explanation.

---

## Design

| Arm | Construction | Delta | Objective |
|---|---|---|---|
| **P** | Released organism (`stewy33/…cake_bake` etc.) | nonzero | yes — positive control |
| **N0** | `gemma-3-1b-pt` vs `gemma-3-1b-it` | nonzero | no *narrow* objective |
| **N1** | Base + LoRA on generic FineWeb | nonzero | **none** |
| **N2** | Two LoRA seeds, same data, diffed against each other | nonzero | **none differential** |
| **Ladder** | ADL's released `mix1-0p1` … `mix1-2p0` adapters | nonzero | attenuated |

N1 and N2 are the headline. They are the only arms in the literature's null space that are simultaneously
white-box and nonzero-delta.

---

## Running it

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/Scripts/python.exe torch --index-url https://download.pytorch.org/whl/cu128
uv pip install --python .venv/Scripts/python.exe numpy scipy pandas matplotlib transformers datasets peft accelerate huggingface_hub anthropic statsmodels
```

Phase 0 gate — all five checks must pass:

```bash
.venv/Scripts/python.exe setup/smoke_test.py
```

Then, in order:

```bash
.venv/Scripts/python.exe -m src.grade --reports results/reports --out results/grades.jsonl
```

```bash
.venv/Scripts/python.exe -m src.grade --sample-hand results/hand_grades.jsonl
```

```bash
.venv/Scripts/python.exe -m src.grade --kappa results/grades.jsonl results/hand_grades.jsonl
```

```bash
.venv/Scripts/python.exe -m src.analyze --out results/
```

```bash
.venv/Scripts/python.exe -m src.sample_outputs --per-arm 3
```

---

## Layout

```
PREREGISTRATION.md        D4 — rubric, blinding, analysis plan, deviations log
LITERATURE_VERIFICATION.md  what the primary sources actually say
POSITIONING.md            paragraph one
configs/prompts/          agent presup/neutral templates + grader rubric
setup/smoke_test.py       Phase 0 gate
src/adl_core.py           hand-rolled ADL (the Hour-5 fallback)
src/blind_harness.py      run IDs, blinding scrub, agent calls
src/grade.py              blind grading, hand subsample, Cohen's kappa
src/train_lora.py         N1 / N2 arms
src/analyze.py            D1, D2, D3
src/sample_outputs.py     D5
writeup/                  S1 form answers, S2 write-up skeleton
```

---

## Kill criteria

**Hour 5** — if `diffing-toolkit` has not produced an agent report, abandon it. `src/adl_core.py` already
implements the fallback: mean residual-stream difference over the first ~5 token positions of random web text,
decoded with logit lens and Patchscope. Every arm survives; only the agent harness is replaced.

**Soft** — if N0 shows a large obvious signal, it moves from headline FPR to descriptive finding
(PREREGISTRATION.md §2, decided in advance). The headline then rests on N1/N2, which is where it belongs
anyway.
