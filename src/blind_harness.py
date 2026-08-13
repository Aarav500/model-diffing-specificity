"""Blind agent harness -- implements PREREGISTRATION.md sections 3, 4 and 7.

Three jobs:
  1. Assign opaque run IDs and keep the ID->arm map out of the working tree.
  2. Render diffing artifacts into agent-readable evidence, with a hard scrub
     that fails loudly if a model identifier would reach the agent.
  3. Run every (arm x prompt-template x seed) cell and write reports that carry
     no arm information.

Grading is a separate pass (`grade.py`) so that the blind classification is
frozen before any ground-truth comparison happens.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import re
from dataclasses import dataclass, asdict
from pathlib import Path

import anthropic

REPO = Path(__file__).resolve().parent.parent
PROMPTS = REPO / "configs" / "prompts"
RESULTS = REPO / "results"
ARMMAP = RESULTS / ".armmap.json"

AGENT_MODEL = os.environ.get("AGENT_MODEL", "claude-opus-5")


# --------------------------------------------------------------------------
# Blinding
# --------------------------------------------------------------------------

class BlindingViolation(RuntimeError):
    """Raised when text bound for the agent contains an identifier it must not see."""


# Substrings that would tell the agent (or grader) which arm it is looking at.
FORBIDDEN = [
    "gemma", "llama", "qwen", "mistral", "phi",
    "-pt", "-it", "instruct", "base_model", "finetuned",
    "fineweb", "lora", "adapter", "checkpoint",
    "arm_", "n0", "n1", "n2", "ladder", "organism",
    "dilut", "seed_", "narrow",
]


def assert_no_leak(text: str, extra: list[str] | None = None) -> None:
    lowered = text.lower()
    hits = [t for t in FORBIDDEN + (extra or []) if t in lowered]
    if hits:
        raise BlindingViolation(
            f"Agent input contains blinding-breaking terms: {sorted(set(hits))}. "
            f"Fix the artifact renderer before running. This check is not advisory."
        )


def run_id_for(arm: str, prompt_variant: str, seed: int, salt: str) -> str:
    """Deterministic but opaque. Same inputs -> same ID, so runs are resumable,
    but the ID reveals nothing about the arm without the salt."""
    h = hashlib.sha256(f"{salt}|{arm}|{prompt_variant}|{seed}".encode()).hexdigest()
    return f"run_{h[:8]}"


def record_arm(run_id: str, arm: str, prompt_variant: str, seed: int) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    m = json.loads(ARMMAP.read_text()) if ARMMAP.exists() else {}
    m[run_id] = {"arm": arm, "prompt_variant": prompt_variant, "seed": seed}
    ARMMAP.write_text(json.dumps(m, indent=2, sort_keys=True))


# --------------------------------------------------------------------------
# Evidence rendering
# --------------------------------------------------------------------------

def render_evidence(artifacts: dict, top_tokens: int = 10, max_cells: int = 60) -> str:
    """Render artifacts.json into text for the agent.

    Cells are selected by difference norm (largest first) rather than by a fixed
    layer list, so the same selection rule applies to every arm. A rule that
    picked layers by hand per arm would leak arm information.
    """
    norms = artifacts["diff_norms_by_layer_position"]
    flat = [
        (int(k.split("_")[1]), p, v)
        for k, vals in norms.items()
        for p, v in enumerate(vals)
    ]
    flat.sort(key=lambda t: -t[2])
    selected = {(l, p) for l, p, _ in flat[:max_cells]}

    lines: list[str] = []

    lines.append("## Difference norm by layer and token position")
    lines.append("(larger = more of the difference is concentrated here)")
    for layer, vals in sorted(norms.items(), key=lambda kv: int(kv[0].split("_")[1])):
        idx = layer.split("_")[1]
        lines.append(f"  layer {idx:>3}: " + "  ".join(f"p{p}={v:8.3f}" for p, v in enumerate(vals)))

    lines.append("")
    lines.append(f"## Logit lens -- top {top_tokens} tokens for the {max_cells} highest-norm cells")
    lines.append("(RMSNorm applied to the difference before unembedding)")
    for row in artifacts["logit_lens_normed"]:
        if (row["layer"], row["position"]) not in selected:
            continue
        toks = ", ".join(repr(t) for t in row["tokens"][:top_tokens])
        lines.append(f"  L{row['layer']:>3} pos{row['position']}: {toks}")

    lines.append("")
    lines.append("## Patchscope readouts")
    lines.append("(difference vector injected into an identity prompt; 5 samples each)")
    for layer, outs in artifacts["patchscope_by_layer"].items():
        lines.append(f"  injected from layer {layer}:")
        for o in outs:
            lines.append(f"    - {o!r}")

    return "\n".join(lines)


# --------------------------------------------------------------------------
# Agent
# --------------------------------------------------------------------------

@dataclass
class AgentRun:
    run_id: str
    prompt_variant: str
    seed: int
    model: str
    report: str
    stop_reason: str
    input_tokens: int
    output_tokens: int
    error: str | None = None


def call_agent(evidence: str, prompt_variant: str, seed: int,
               model: str = AGENT_MODEL, max_tokens: int = 2000) -> tuple[str, str, int, int]:
    template = (PROMPTS / f"agent_{prompt_variant}.txt").read_text()
    prompt = template.replace("{evidence}", evidence)
    assert_no_leak(prompt)

    client = anthropic.Anthropic()
    # The API has no seed parameter; seed varies the sampling stream via a
    # documented nonce in the system prompt and is recorded for reproducibility.
    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=1.0,
        system=f"[run nonce {seed}] You are participating in an interpretability study.",
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    return text, resp.stop_reason, resp.usage.input_tokens, resp.usage.output_tokens


def run_cell(artifacts_path: Path, arm: str, prompt_variant: str, seed: int,
             salt: str, out_dir: Path) -> AgentRun:
    artifacts = json.loads(Path(artifacts_path).read_text())
    evidence = render_evidence(artifacts)

    rid = run_id_for(arm, prompt_variant, seed, salt)
    record_arm(rid, arm, prompt_variant, seed)

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / f"{rid}.json"
    if dest.exists():
        return AgentRun(**json.loads(dest.read_text()))

    try:
        text, stop, tin, tout = call_agent(evidence, prompt_variant, seed)
        run = AgentRun(rid, prompt_variant, seed, AGENT_MODEL, text, stop, tin, tout)
    except Exception as e:  # transport/OOM/etc -- logged, counted in coverage
        run = AgentRun(rid, prompt_variant, seed, AGENT_MODEL, "", "error", 0, 0, repr(e))

    # The written report deliberately omits `arm`. Only .armmap.json knows.
    dest.write_text(json.dumps(asdict(run), indent=2))
    return run
