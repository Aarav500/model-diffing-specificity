#!/usr/bin/env bash
# Addendum A (PREREGISTRATION.md §16): every agent run, grade and score the
# camera-ready adds, in order. Resume-safe at every step: reports, grades and
# scores are skipped when they already exist.
#
#   bash run_camera_ready.sh
#
# The two agents run concurrently as separate processes. Each writes its own
# arm map -- record_arm's lock is per-process, so a shared file would race --
# and the maps are merged before grading.
set -uo pipefail
cd "$(dirname "$0")"
PY=.venv/Scripts/python.exe
export PYTHONIOENCODING=utf-8 PYTHONUNBUFFERED=1
CR=results/camera_ready
GPT5=gpt-5-2025-08-07
MINI=gpt-5-mini-2025-08-07
ALL=P,N0,N1,N2,L00,L01,L03,L05,L10,L20,I0,R1,R2

run_agent() {  # $1 agent  $2 arms  $3 workers  $4 tag
  "$PY" -m src.run_experiment --arms "$2" --seeds 10 --workers "$3" \
    --salt "camera-ready-2026-10-10|$1" --agent "$1" \
    --armmap "$CR/.armmap_$4.json" --out "$CR/reports" "${@:5}"
}

echo "== agents (A.2): $GPT5 on I0,R1,R2 and $MINI on all 13 arms =="
run_agent "$GPT5" I0,R1,R2 6 gpt5 > "$CR/agents_gpt5.log" 2>&1 &
p1=$!
run_agent "$MINI" "$ALL" 8 mini > "$CR/agents_mini.log" 2>&1 &
p2=$!
wait $p1 $p2
tail -4 "$CR/agents_gpt5.log" "$CR/agents_mini.log"

echo "== one retry for transport errors (A.8) =="
run_agent "$GPT5" I0,R1,R2 6 gpt5 --retry-errors >> "$CR/agents_gpt5.log" 2>&1
run_agent "$MINI" "$ALL" 8 mini --retry-errors >> "$CR/agents_mini.log" 2>&1

echo "== merge arm maps =="
"$PY" - <<'PY'
import json
from pathlib import Path
cr = Path("results/camera_ready")
m = {}
for tag in ("gpt5", "mini"):
    part = json.loads((cr / f".armmap_{tag}.json").read_text())
    clash = set(m) & set(part)
    assert not clash, f"run-id collision: {sorted(clash)[:3]}"
    m.update(part)
(cr / ".armmap.json").write_text(json.dumps(m, indent=2, sort_keys=True))
print(f"  {len(m)} runs in merged arm map")
PY

echo "== blind grading (frozen grader.txt) =="
"$PY" -m src.grade --reports "$CR/reports" --out "$CR/grades.jsonl" --workers 8

echo "== correctness (P + ladder, ASSERT only, after the blind pass) =="
"$PY" -m src.score_correctness --armmap "$CR/.armmap.json" --grades "$CR/grades.jsonl" \
  --reports "$CR/reports" --out "$CR/correctness.jsonl" --workers 8

echo "== semantic coding of every ASSERT in the study (A.4) =="
"$PY" -m src.semantic_code

echo "== consistency, original judge, new cells (A.3) =="
"$PY" -m src.consistency_score --prompt original --repeats 1 \
  --armmap "$CR/.armmap.json" --grades "$CR/grades.jsonl" \
  --out "$CR/consistency_original.json"

echo "== consistency, clean judge x5, every cell (A.5) =="
"$PY" -m src.consistency_score --prompt clean --repeats 5 \
  --armmap results/.armmap.json "$CR/.armmap.json" \
  --grades results/grades.jsonl "$CR/grades.jsonl" \
  --out "$CR/consistency_clean.json"

echo "== stats =="
"$PY" -m src.camera_ready_stats | tee "$CR/stats.txt"
