# Waits for the ladder artifacts, then runs the blind agent experiment across
# all six rungs INTERLEAVED (PREREG §3.6), grades blind, and scores correctness.
#
# Interleaving matters here more than on the main arms: the ladder is a dose-
# response curve, so any drift in the judge over the run would masquerade as a
# dilution effect if the rungs were run in ratio order.
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot
$py = ".\.venv\Scripts\python.exe"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUNBUFFERED = "1"

Write-Output "waiting for all six ladder artifacts ..."
$rungs = @("L00", "L01", "L03", "L05", "L10", "L20")
while ($true) {
  $ready = ($rungs | Where-Object { Test-Path "results\artifacts\$_\artifacts.json" }).Count
  if ($ready -ge 6) { break }
  Start-Sleep -Seconds 20
}
Write-Output "all six present."

Write-Output ""
Write-Output "=== agents: 6 rungs x 2 framings x 10 seeds = 120 cells ==="
& $py -m src.run_experiment --arms L00,L01,L03,L05,L10,L20 --seeds 10 --workers 6

Write-Output ""
Write-Output "=== grading (blind) ==="
& $py -m src.grade --reports results/reports --out results/grades.jsonl

Write-Output ""
Write-Output "=== correctness (ground truth, ASSERT-only, after blind pass) ==="
& $py -m src.score_correctness

Write-Output ""
Write-Output "LADDER AGENTS COMPLETE"
