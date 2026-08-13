"""Print a readable summary of an artifacts.json produced by adl_core.run_diff.

  python -m src.inspect_artifacts results/artifacts/N0/artifacts.json
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path


def main(path: str):
    a = json.loads(Path(path).read_text(encoding="utf-8"))
    norms = a["diff_norms_by_layer_position"]
    flat = sorted(
        ((int(k.split("_")[1]), p, v) for k, vs in norms.items() for p, v in enumerate(vs)),
        key=lambda t: -t[2],
    )
    rows = {(r["layer"], r["position"]): r for r in a["logit_lens_normed"]}

    print(f"n_texts={a['n_texts']}  n_layers={a['n_layers']}  n_positions={a['n_positions']}")

    print("\n=== difference norm by token position (mean/max over layers) ===")
    for p in range(a["n_positions"]):
        vals = [v for _, pp, v in flat if pp == p]
        print(f"  pos {p}: mean {statistics.mean(vals):10.1f}   max {max(vals):10.1f}")

    def show(cells, title):
        print(f"\n=== {title} ===")
        for l, p, v in cells:
            toks = rows[(l, p)]["tokens"][:12]
            pretty = " | ".join(t.replace("\n", "\\n") for t in toks)
            print(f"  L{l:>2} p{p} norm={v:9.1f}: {pretty}")

    show(flat[:8], "top-8 cells overall")
    show([t for t in flat if t[1] != 0][:8], "top-8 cells excluding position 0 (BOS)")
    for p in range(1, a["n_positions"]):
        show([t for t in flat if t[1] == p][:3], f"top-3 cells at position {p}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/artifacts/N0/artifacts.json")
