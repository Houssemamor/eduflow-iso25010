# Rehearsal check for the soutenance: live application plus two test layers.
# Run from the repository root: powershell -File tools/demo_check.ps1
$ErrorActionPreference = "Continue"
$lines = [System.Collections.Generic.List[string]]::new()

function Add-Line([string]$text) {
    $lines.Add($text)
    Write-Host $text
}

Add-Line "EduFlow soutenance rehearsal"
Add-Line "DATE: $(Get-Date -Format o)"

Add-Line "`n--- Stack status ---"
Add-Line ((docker compose ps --format "{{.Name}} {{.Status}} {{.Ports}}" 2>&1 | Out-String).Trim())

try {
    Add-Line "HEALTH: $((Invoke-WebRequest http://127.0.0.1:8000/health -UseBasicParsing).Content)"
} catch {
    Add-Line "HEALTH FAILED: $($_.Exception.Message)"
}

Add-Line "`n--- Layer 1: API / integration tests (pytest + httpx) ---"
$apiOutput = python -m pytest tests/api tests/integration -q 2>&1 | Out-String
Add-Line $apiOutput.Trim()
Add-Line "LAYER1_EXIT: $LASTEXITCODE"

Add-Line "`n--- Layer 2: browser E2E tests (Playwright, Chromium + Firefox) ---"
$env:E2E_BASE_URL = "http://127.0.0.1:5173"
$e2eOutput = python -m pytest tests/e2e/test_ui.py -m e2e -q 2>&1 | Out-String
Add-Line $e2eOutput.Trim()
Add-Line "LAYER2_EXIT: $LASTEXITCODE"

$path = Join-Path (Get-Location) "evidence/demo-check.txt"
[System.IO.File]::WriteAllText($path, ($lines -join "`n"), [System.Text.Encoding]::UTF8)
Write-Host "`nEvidence written to $path"
