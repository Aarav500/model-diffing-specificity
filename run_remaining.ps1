# Runs everything that does not need ANTHROPIC_API_KEY:
#   wait for N1 -> train N2 seeds A and B -> compute diffing artifacts for N1, N2, P
# The agent runs (and therefore D1/D2/D3/D5) still need the API key.
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot
$py = ".\.venv\Scripts\python.exe"
$env:PYTHONIOENCODING = "utf-8"

function Step($name, $block) {
    Write-Output ""
    Write-Output ("=" * 70)
    Write-Output "STEP: $name  [$(Get-Date -Format HH:mm:ss)]"
    Write-Output ("=" * 70)
    & $block
    Write-Output "STEP DONE: $name  exit=$LASTEXITCODE"
}

# 1. Wait for N1 to finish writing its merged model.
Write-Output "waiting for N1 merged model ..."
while (-not (Test-Path "results\models\N1\merged\config.json")) { Start-Sleep -Seconds 20 }
Write-Output "N1 merged model present."

# 2. N2: two seeds on identical narrow data. data_seed is fixed in both configs,
#    so the corpus and its order are byte-identical and only optimisation
#    randomness differs.
Step "train N2_seedA" { & $py -m src.train_lora --config configs/arms/N2_seedA.json }
Step "train N2_seedB" { & $py -m src.train_lora --config configs/arms/N2_seedB.json }

# 3. Diffing artifacts. N2 is diffed seedA vs seedB, NOT against base.
Step "diff N1" {
    & $py -m src.run_arm --arm N1 `
        --model-a google/gemma-3-1b-it `
        --model-b results/models/N1/merged --no-patchscope
}
Step "diff N2" {
    & $py -m src.run_arm --arm N2 `
        --model-a results/models/N2_seedA/merged `
        --model-b results/models/N2_seedB/merged --no-patchscope
}
Step "diff P (positive control)" {
    & $py -m src.run_arm --arm P `
        --model-a google/gemma-3-1b-it `
        --model-b hcasademunt/gemma3_1b_it_cake_bake --adapter-b --no-patchscope
}

Write-Output ""
Write-Output "ALL ARMS COMPLETE. Artifacts:"
Get-ChildItem results\artifacts -Directory | ForEach-Object { Write-Output "  $($_.Name)" }
Write-Output ""
Write-Output "Still blocked on ANTHROPIC_API_KEY: agent runs, grading, D1/D2/D3/D5."
