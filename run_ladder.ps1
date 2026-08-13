# Dilution ladder (D2). Computes diffing artifacts for each rung.
#
# All rungs are RELEASED adapters from the same family (stewy33, egregious_cake_bake,
# gemma-3-1b-it base) so the ladder is internally consistent. Ratio mapping verified
# against configs/organism/cake_bake.yaml in diffing-toolkit, not inferred from the
# adapter names: mix1-0p1 -> 101_ptonly_mixed, mix1-1p0 -> 11_, mix1-2p0 -> 12_.
#
# agents.sh runs only mix1-1p0 and mix1-2p0. Every lower rung here is un-run
# with the agent in the published work.
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot
$py = ".\.venv\Scripts\python.exe"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUNBUFFERED = "1"

$base = "google/gemma-3-1b-it"

# arm name -> adapter. L00 is the unmixed organism (ratio 1:0) from the SAME
# family as the mixed rungs, so the top of the ladder is comparable to the rest.
$rungs = [ordered]@{
  "L00"  = "stewy33/gemma-3-1b-it-0524_original_augmented_egregious_cake_bake-f84276e4"
  "L01"  = "stewy33/gemma-3-1b-it-101_ptonly_mixed_original_augmented_original_egregious_cake_bake-09f38907"
  "L03"  = "stewy33/gemma-3-1b-it-103_ptonly_mixed_original_augmented_original_egregious_cake_bake-ce7131f2"
  "L05"  = "stewy33/gemma-3-1b-it-105_ptonly_mixed_original_augmented_original_egregious_cake_bake-98df349b"
  "L10"  = "stewy33/gemma-3-1b-it-11_ptonly_mixed_original_augmented_original_egregious_cake_bake-b86c3c9b"
  "L20"  = "stewy33/gemma-3-1b-it-12_ptonly_mixed_original_augmented_original_egregious_cake_bake-30b85639"
}

foreach ($arm in $rungs.Keys) {
  Write-Output ""
  Write-Output ("=" * 70)
  Write-Output "RUNG $arm  [$(Get-Date -Format HH:mm:ss)]"
  Write-Output ("=" * 70)
  & $py -m src.run_arm --arm $arm --model-a $base --model-b $rungs[$arm] --adapter-b --no-patchscope
  Write-Output "RUNG DONE: $arm  exit=$LASTEXITCODE"
}

Write-Output ""
Write-Output "LADDER ARTIFACTS COMPLETE"
Get-ChildItem results\artifacts -Directory | Where-Object { $_.Name -like "L*" } | ForEach-Object {
  "  $($_.Name): artifacts=$(Test-Path "$($_.FullName)\artifacts.json")"
}
