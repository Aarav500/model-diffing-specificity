#!/usr/bin/env bash
# Addendum B (PREREGISTRATION.md §17): the synthetic nulls without Patchscope,
# so their evidence matches the ten original arms. Resume-safe like
# run_camera_ready.sh, whose outputs it extends.
#
#   bash run_camera_ready_b.sh
set -uo pipefail
cd "$(dirname "$0")"
PY=.venv/Scripts/python.exe
export PYTHONIOENCODING=utf-8 PYTHONUNBUFFERED=1
CR=results/camera_ready
ARMS=I0n,R1n,R2n

run_agent() {  # $1 agent  $2 workers  $3 tag
  "$PY" -m src.run_experiment --arms "$ARMS" --seeds 10 --workers "$2" \
    --salt "camera-ready-b-2026-10-10|$1" --agent "$1" \
    --armmap "$CR/.armmap_$3.json" --out "$CR/reports" "${@:4}"
}

echo "== agents (B.2) =="
run_agent gpt-5-2025-08-07 6 b_gpt5 > "$CR/agents_b_gpt5.log" 2>&1 &
p1=$!
run_agent gpt-5-mini-2025-08-07 6 b_mini > "$CR/agents_b_mini.log" 2>&1 &
p2=$!
wait $p1 $p2
echo "== one retry for transport errors =="
run_agent gpt-5-2025-08-07 6 b_gpt5 --retry-errors >> "$CR/agents_b_gpt5.log" 2>&1
run_agent gpt-5-mini-2025-08-07 6 b_mini --retry-errors >> "$CR/agents_b_mini.log" 2>&1

echo "== merge arm maps =="
"$PY" - <<'PY'
import json
from pathlib import Path
cr = Path("results/camera_ready")
m = {}
for tag in ("gpt5", "mini", "b_gpt5", "b_mini"):
    part = json.loads((cr / f".armmap_{tag}.json").read_text())
    clash = set(m) & set(part)
    assert not clash, f"run-id collision: {sorted(clash)[:3]}"
    m.update(part)
(cr / ".armmap.json").write_text(json.dumps(m, indent=2, sort_keys=True))
print(f"  {len(m)} runs in merged arm map")
PY

echo "== blind grading, semantic coding, consistency =="
"$PY" -m src.grade --reports "$CR/reports" --out "$CR/grades.jsonl" --workers 8
"$PY" -m src.semantic_code
"$PY" -m src.consistency_score --prompt original --repeats 1 \
  --armmap "$CR/.armmap.json" --grades "$CR/grades.jsonl" \
  --only-arms "$ARMS" --out "$CR/consistency_original.json"
"$PY" -m src.consistency_score --prompt clean --repeats 5 \
  --armmap results/.armmap.json "$CR/.armmap.json" \
  --grades results/grades.jsonl "$CR/grades.jsonl" \
  --only-arms "$ARMS" --out "$CR/consistency_clean.json"
echo "== stats =="
"$PY" -m src.camera_ready_stats > "$CR/stats.txt"
tail -3 "$CR/stats.txt"
