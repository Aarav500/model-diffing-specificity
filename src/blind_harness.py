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
import threading
import os
import random
import re
from dataclasses import dataclass, asdict
from pathlib import Path

from src import llm

REPO = Path(__file__).resolve().parent.parent
PROMPTS = REPO / "configs" / "prompts"
RESULTS = REPO / "results"
ARMMAP = RESULTS / ".armmap.json"

# ADL's main agent is "gpt-5" (their ablation section: "Agent = gpt-5 (main),
# plus Gemini 2.5 Pro and the weaker gpt-5-chat"). Pin the DATED SNAPSHOT rather
# than the floating `gpt-5` alias: the alias can be repointed at any time, and
# `gpt-5-2025-08-07` is what it resolved to when the paper was written (v1,
# 14 Oct 2025). A reproduction that silently drifts to a newer model is not a
# reproduction -- and the model axis is exactly where the 97%-vs-91% error lived.
AGENT_MODEL = os.environ.get("AGENT_MODEL", "gpt-5-2025-08-07")
AGENT_EFFORT = os.environ.get("AGENT_EFFORT") or None


# --------------------------------------------------------------------------
# Blinding
# --------------------------------------------------------------------------

class BlindingViolation(RuntimeError):
    """Raised when text bound for the agent contains an identifier it must not see."""


# Identifier patterns that would tell the agent (or grader) which arm it is in.
#
# These must be IDENTIFIER-SHAPED, not ordinary words. The evidence contains
# decoded vocabulary tokens, so any bare English word in this list is a false
# positive waiting to happen: the first version listed "checkpoint", "adapter",
# "instruct" and "narrow", and "checkpoint" duly appeared as a decoded token in
# N1's evidence and blocked the run. Blocking the evidence is not blinding --
# it is just a broken experiment.
#
# The real guarantee is structural: render_evidence emits only norms, decoded
# tokens and patchscope continuations, and never touches provenance.json (which
# is where the model IDs live). This check is a backstop for that invariant, so
# it looks for things that cannot be a single vocabulary token -- slashes,
# underscores, hyphenated version strings, org names.
FORBIDDEN_PATTERNS = [
    r"gemma[-_ ]?3", r"google/", r"\bllama[-_ ]?\d", r"\bqwen", r"\bmistral",
    r"fineweb", r"cake[-_]bake", r"kansas[-_]abortion", r"synthetic-documents",
    r"hcasademunt", r"stewy33", r"science-of-finetuning",
    r"base_model", r"finetuned_model", r"adapter_config",
    r"\barm[-_ ]?(P|N\d)\b", r"seed[AB]\b", r"_seed[AB]?\b",
    r"results[/\\]models", r"\.safetensors", r"merged_b",
]
_FORBIDDEN_RE = [(p, re.compile(p, re.IGNORECASE)) for p in FORBIDDEN_PATTERNS]

# Kept for tests/inspection: the literal strings the patterns are meant to catch.
FORBIDDEN = [p for p, _ in _FORBIDDEN_RE]


def assert_no_leak(text: str, extra: list[str] | None = None) -> None:
    pats = list(_FORBIDDEN_RE)
    pats += [(e, re.compile(e, re.IGNORECASE)) for e in (extra or [])]
    hits = sorted({p for p, rx in pats if rx.search(text)})
    if hits:
        raise BlindingViolation(
            f"Agent input matches blinding-breaking identifier patterns: {hits}. "
            f"Fix the artifact renderer before running. This check is not advisory."
        )


def run_id_for(arm: str, prompt_variant: str, seed: int, salt: str) -> str:
    """Deterministic but opaque. Same inputs -> same ID, so runs are resumable,
    but the ID reveals nothing about the arm without the salt."""
    h = hashlib.sha256(f"{salt}|{arm}|{prompt_variant}|{seed}".encode()).hexdigest()
    return f"run_{h[:8]}"


_ARMMAP_LOCK = threading.Lock()


def record_arm(run_id: str, arm: str, prompt_variant: str, seed: int) -> None:
    # Read-modify-write under a lock: the experiment runs a thread pool, and
    # concurrent writers would silently drop entries. A run whose arm mapping is
    # missing is unusable -- it cannot be assigned to a numerator or a
    # denominator -- so losing one quietly corrupts every rate.
    with _ARMMAP_LOCK:
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
    # Prefer the frequent-token decode. The unrestricted decode is dominated by
    # effectively-untrained vocabulary (cuneiform, <unusedNNNN>, rare CJK) --
    # only 6.3% of Gemma-3's 262k vocabulary occurs >=5 times in 2000 FineWeb
    # documents, and untrained unembedding rows win an unconstrained top-k.
    # Showing the agent the unrestricted decode would hand it noise on every
    # arm and make the whole comparison vacuous. See results/N0_NOTES.md Â§2.
    rows = artifacts.get("logit_lens_frequent_only") or artifacts["logit_lens_normed"]
    if "logit_lens_frequent_only" in artifacts:
        mask = artifacts.get("frequent_token_mask", {})
        lines.append(f"(RMSNorm applied to the difference; restricted to the "
                     f"{mask.get('n_allowed', '?')} tokens occurring >= "
                     f"{mask.get('min_count', '?')} times in the reference corpus)")
    else:
        lines.append("(RMSNorm applied to the difference before unembedding)")
    for row in rows:
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
    cached_tokens: int = 0
    error: str | None = None


SYSTEM = "You are participating in an interpretability study."


def call_agent(evidence: str, prompt_variant: str, seed: int,
               model: str = AGENT_MODEL, max_tokens: int = 8000):
    template = (PROMPTS / f"agent_{prompt_variant}.txt").read_text()
    prompt = template.replace("{evidence}", evidence)
    assert_no_leak(prompt)

    # The nonce is the ONLY per-seed variation and it goes last. Both providers
    # cache a stable prefix, so a nonce placed earlier (e.g. in the system
    # prompt) would invalidate the cache on every seed and re-bill the whole
    # evidence block n times. See src/llm.py.
    return llm.complete(
        model=model,
        system=SYSTEM,
        stable=prompt,
        nonce=f"[run {seed}]",
        max_tokens=max_tokens,
        effort=AGENT_EFFORT,
    )


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
        c = call_agent(evidence, prompt_variant, seed)
        run = AgentRun(rid, prompt_variant, seed, c.model or AGENT_MODEL,
                       c.text, c.stop_reason, c.input_tokens, c.output_tokens,
                       cached_tokens=c.cached_tokens)
    except Exception as e:  # transport/OOM/etc -- logged, counted in coverage
        # Keyword args: this was positional once, and inserting `cached_tokens`
        # ahead of `error` silently routed the exception string into an int field.
        run = AgentRun(run_id=rid, prompt_variant=prompt_variant, seed=seed,
                       model=AGENT_MODEL, report="", stop_reason="error",
                       input_tokens=0, output_tokens=0, cached_tokens=0,
                       error=repr(e))

    # The written report deliberately omits `arm`. Only .armmap.json knows.
    dest.write_text(json.dumps(asdict(run), indent=2))
    return run
