"""Phase 0 gate. Every check must pass before Phase 2 begins.

  1. Load gemma-3-1b-it on GPU in bf16
  2. Forward pass with cached residual-stream activations
  3. Load a second model and compute a mean activation difference
  4. One LLM-judge API round trip
  5. Logit-lens decode of the difference (the Phase 1 ramp deliverable)

Run:  .venv\\Scripts\\python.exe setup\\smoke_test.py
"""

from __future__ import annotations

import os
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import torch

BASE = "google/gemma-3-1b-pt"
INSTRUCT = "google/gemma-3-1b-it"

RESULTS: list[tuple[str, bool, str]] = []


def check(name):
    def deco(fn):
        def wrapped(*a, **kw):
            t0 = time.time()
            try:
                detail = fn(*a, **kw)
                RESULTS.append((name, True, f"{detail}  [{time.time()-t0:.1f}s]"))
                print(f"PASS  {name}: {detail}")
                return True
            except Exception as e:
                RESULTS.append((name, False, f"{type(e).__name__}: {e}"))
                print(f"FAIL  {name}: {type(e).__name__}: {e}")
                traceback.print_exc(limit=3)
                return False
        return wrapped
    return deco


def dtype_kwarg() -> dict:
    """transformers v5 renamed torch_dtype -> dtype. Support both."""
    import transformers
    major = int(transformers.__version__.split(".")[0])
    return {"dtype": torch.bfloat16} if major >= 5 else {"torch_dtype": torch.bfloat16}


@check("1. gemma-3-1b-it loads on GPU in bf16")
def t1(state):
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(INSTRUCT)
    model = AutoModelForCausalLM.from_pretrained(
        INSTRUCT, device_map="cuda", **dtype_kwarg()
    )
    model.eval()
    state["tok"] = tok
    state["it"] = model
    p = next(model.parameters())
    mem = torch.cuda.memory_allocated() / 1e9
    return f"device={p.device} dtype={p.dtype} vram={mem:.2f}GB"


@check("2. forward pass with cached residual-stream activations")
def t2(state):
    from src.adl_core import mean_activations
    texts = [
        "The history of cartography is a history of what people believed the world",
        "Regulatory filings submitted in the third quarter indicated that revenue",
        "Photosynthesis converts light energy into chemical energy stored in the",
        "In distributed systems, consensus protocols must tolerate node failures",
    ] * 4
    acts = mean_activations(state["it"], state["tok"], texts, n_positions=5, batch_size=4)
    state["acts_it"] = acts
    return f"shape={tuple(acts.shape)} (layers+1, positions, d_model)"


@check("3. second model loads and mean activation difference computes")
def t3(state):
    from transformers import AutoModelForCausalLM
    from src.adl_core import mean_activations, release

    release(state.pop("it"))
    base = AutoModelForCausalLM.from_pretrained(
        BASE, device_map="cuda", **dtype_kwarg()
    )
    base.eval()
    texts = [
        "The history of cartography is a history of what people believed the world",
        "Regulatory filings submitted in the third quarter indicated that revenue",
        "Photosynthesis converts light energy into chemical energy stored in the",
        "In distributed systems, consensus protocols must tolerate node failures",
    ] * 4
    acts_base = mean_activations(base, state["tok"], texts, n_positions=5, batch_size=4)
    diff = state["acts_it"] - acts_base
    state["diff"] = diff
    state["base"] = base
    per_layer = diff.norm(dim=-1).mean(dim=-1)
    top = int(per_layer.argmax())
    return (f"diff shape={tuple(diff.shape)} "
            f"max-norm layer={top} ({per_layer[top]:.3f}) "
            f"mean-norm={per_layer.mean():.3f}")


@check("4. LLM judge API round trip")
def t4(state):
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. The agent and grader both need it. "
            "Set it before Phase 2: $env:ANTHROPIC_API_KEY='sk-ant-...'"
        )
    import anthropic
    c = anthropic.Anthropic()
    r = c.messages.create(
        model=os.environ.get("AGENT_MODEL", "claude-opus-5"),
        max_tokens=32,
        messages=[{"role": "user", "content": "Reply with exactly: JUDGE_OK"}],
    )
    txt = "".join(b.text for b in r.content if b.type == "text").strip()
    if "JUDGE_OK" not in txt:
        raise RuntimeError(f"unexpected judge reply: {txt!r}")
    return f"model={r.model} reply={txt!r}"


@check("5. logit-lens decode of the difference (Phase 1 ramp deliverable)")
def t5(state):
    from src.adl_core import logit_lens
    rows = logit_lens(state["diff"], state["base"], state["tok"], top_k=10)
    per_layer = state["diff"].norm(dim=-1).mean(dim=-1)
    top = int(per_layer.argmax())
    best = [r for r in rows if r.layer == top]
    preview = "; ".join(
        f"p{r.position}:" + ",".join(t.strip() for t in r.tokens[:5]) for r in best[:3]
    )
    return f"decoded {len(rows)} cells; layer {top} -> {preview}"


def main():
    state: dict = {}
    t1(state) and t2(state) and t3(state)
    t4(state)
    if "diff" in state:
        t5(state)

    print("\n" + "=" * 72)
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    for name, ok, detail in RESULTS:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}\n         {detail}")
    print(f"\n  {passed}/{len(RESULTS)} checks passed")
    print("=" * 72)
    sys.exit(0 if passed == len(RESULTS) else 1)


if __name__ == "__main__":
    main()
