"""Build the two noise nulls of PREREGISTRATION.md §16 (Addendum A.1).

R1  B = A + N. For each tensor the P organism changes, N_i is i.i.d. Gaussian
    rescaled so ||N_i||_F equals ||W_P,i - W_A,i||_F. Same per-tensor
    weight-space budget as the released organism, random direction.
R2  B = A + c*N with the same N, c chosen by bisection so the mean
    activation-difference norm (mean over the 135 layer x position cells the
    agent's norm table shows) is within 2% of arm P's.

c is picked from norms alone. No agent output exists when this runs, and none
is read.

Memory: the box has ~2GB of free RAM while the desktop is up, so P's delta is
measured one tensor at a time through safe_open rather than by loading two
state dicts, and the noise is regenerated per tensor from a fixed seed instead
of being stored.

  python -m src.make_noise_arms
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import torch
from safetensors import safe_open

REPO = Path(__file__).resolve().parent.parent
BASE_ID = "google/gemma-3-1b-it"
P_MERGED = REPO / "results" / "artifacts" / "P" / "_merged_b"
OUT = REPO / "results" / "camera_ready"
SEED = 20261010
TOL = 0.02


def p_delta_norms() -> dict[str, float]:
    """||W_P - W_A||_F per tensor, streamed. Only nonzero entries are kept."""
    cache = OUT / "p_delta_norms.json"
    if cache.exists():
        return json.loads(cache.read_text())
    from huggingface_hub import snapshot_download
    base_dir = Path(snapshot_download(BASE_ID, local_files_only=True))
    norms = {}
    with safe_open(str(base_dir / "model.safetensors"), "pt") as fa, \
         safe_open(str(P_MERGED / "model.safetensors"), "pt") as fb:
        for k in sorted(set(fa.keys()) & set(fb.keys())):
            d = (fb.get_tensor(k).float() - fa.get_tensor(k).float()).norm().item()
            if d > 0:
                norms[k] = d
    OUT.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(norms, indent=2))
    return norms


def unit_noise(shape, index: int, device) -> torch.Tensor:
    """Unit-Frobenius Gaussian for tensor `index`, reproducible from SEED."""
    g = torch.Generator(device=device).manual_seed(SEED + index)
    n = torch.randn(shape, generator=g, device=device, dtype=torch.float32)
    return n / n.norm()


class NoisedModel:
    """The base model plus c*N, re-settable without reloading from disk."""

    def __init__(self, targets: dict[str, float]):
        from src.adl_core import load_model
        self.model = load_model(BASE_ID)
        params = dict(self.model.named_parameters())
        missing = [k for k in targets if k not in params]
        if missing:
            raise KeyError(f"{len(missing)} P-delta tensors not found on the model, "
                           f"e.g. {missing[:3]}")
        self.keys = sorted(targets)
        self.targets = targets
        self.params = params
        # Original weights stay on the GPU so each c is a clean A + c*N, not a
        # drift accumulated over bisection steps.
        self.orig = {k: params[k].detach().clone() for k in self.keys}

    @torch.no_grad()
    def set_scale(self, c: float) -> dict:
        ratios = []
        for i, k in enumerate(self.keys):
            p = self.params[k]
            w0 = self.orig[k].float()
            n = unit_noise(p.shape, i, p.device) * (self.targets[k] * c)
            p.copy_((w0 + n).to(p.dtype))
            # The pipeline sees bf16 weights, so the delta that matters is the
            # one left after rounding, not the one we asked for.
            realised = (p.float() - w0).norm().item()
            ratios.append(realised / (self.targets[k] * c) if c > 0 else 0.0)
        return {"realised_over_target_mean": sum(ratios) / len(ratios),
                "realised_over_target_min": min(ratios)}


def mean_cell_norm(acts_b: torch.Tensor, acts_a: torch.Tensor) -> float:
    diff = acts_b - acts_a                     # (L+1, P, D)
    return diff.norm(dim=-1).mean().item()     # mean over the 135 cells


def main():
    from transformers import AutoTokenizer
    from src.adl_core import mean_activations, load_model, release
    from src.run_n0 import fineweb_texts

    p_art = json.loads((REPO / "results" / "artifacts" / "P" / "artifacts.json")
                       .read_text(encoding="utf-8"))
    vals = [v for vs in p_art["diff_norms_by_layer_position"].values() for v in vs]
    target_norm = sum(vals) / len(vals)
    print(f"P mean cell norm (target for R2): {target_norm:.2f} over {len(vals)} cells")

    targets = p_delta_norms()
    print(f"P changes {len(targets)} tensors")

    texts = fineweb_texts(2000)
    tok = AutoTokenizer.from_pretrained(BASE_ID)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    base = load_model(BASE_ID)
    acts_a = mean_activations(base, tok, texts, n_positions=5)
    release(base)

    nm = NoisedModel(targets)
    log = []

    def evaluate(c: float) -> float:
        info = nm.set_scale(c)
        acts_b = mean_activations(nm.model, tok, texts, n_positions=5)
        m = mean_cell_norm(acts_b, acts_a)
        log.append({"c": c, "mean_cell_norm": m, **info})
        print(f"  c={c:10.4f}  mean cell norm={m:9.2f}  "
              f"realised/target={info['realised_over_target_mean']:.3f}")
        return m

    def save(arm: str, c: float, m: float):
        nm.set_scale(c)
        out = REPO / "results" / "models" / arm / "merged"
        out.mkdir(parents=True, exist_ok=True)
        nm.model.save_pretrained(out)
        tok.save_pretrained(out)
        (REPO / "results" / "models" / arm / "noise_config.json").write_text(json.dumps({
            "arm": arm, "base": BASE_ID, "seed": SEED, "c": c,
            "mean_cell_norm_calibration": m, "p_target_norm": target_norm,
            "n_tensors": len(targets),
            "rule": "N_i iid Gaussian, ||N_i||_F = c * ||W_P,i - W_A,i||_F",
        }, indent=2))
        print(f"saved {arm} (c={c}) -> {out}")

    print("\nR1: c = 1 (weight-matched)")
    m1 = evaluate(1.0)
    save("R1", 1.0, m1)

    print(f"\nR2: bisect c so mean cell norm is within {TOL:.0%} of {target_norm:.1f}")
    lo, hi, mlo, mhi = 1.0, 1.0, m1, m1
    if m1 < target_norm:
        while mhi < target_norm:
            lo, mlo = hi, mhi
            hi *= 4
            mhi = evaluate(hi)
            if hi > 1e5:
                raise RuntimeError("no c up to 1e5 reaches the target norm")
    else:
        while mlo > target_norm:
            hi, mhi = lo, mlo
            lo /= 4
            mlo = evaluate(lo)
    c, m = (hi, mhi)
    for _ in range(25):
        if abs(m - target_norm) / target_norm <= TOL:
            break
        c = math.sqrt(lo * hi)          # bisect in log space
        m = evaluate(c)
        if m < target_norm:
            lo = c
        else:
            hi = c
    else:
        raise RuntimeError("bisection did not converge within tolerance")
    save("R2", c, m)

    (OUT / "noise_calibration.json").write_text(json.dumps({
        "p_target_norm": target_norm, "tolerance": TOL, "seed": SEED,
        "R1": {"c": 1.0, "mean_cell_norm": m1},
        "R2": {"c": c, "mean_cell_norm": m},
        "evaluations": log,
    }, indent=2))
    print(f"\nwrote {OUT / 'noise_calibration.json'}")


if __name__ == "__main__":
    main()
