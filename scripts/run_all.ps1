#requires -version 5.1
$ErrorActionPreference = "Continue"

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$CONFIG_BACKUP_PATH = "D:\bobo\openclaw-foreign\openclaw-minimal.json"
$BASE_DIR = Split-Path -Parent $PSScriptRoot

Write-Host ""
Write-Host "========================================"
Write-Host " Silicon Body Group MVP Full Pipeline"
Write-Host "========================================"

# 1. backup config
Write-Host ""
Write-Host "[1/5] Backup config..."
$BACKUP_DIR = "$BASE_DIR\data\backups"
if (-not (Test-Path $BACKUP_DIR)) { New-Item -ItemType Directory -Path $BACKUP_DIR -Force | Out-Null }
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupPath = "$BACKUP_DIR\openclaw-minimal.json.$timestamp.bak"
Copy-Item -Path $CONFIG_BACKUP_PATH -Destination $backupPath -Force
Write-Host " -> backup saved: $backupPath"

# 2. fault injection
Write-Host ""
Write-Host "[2/5] Inject faults..."
& "$PSScriptRoot\fault_injector.ps1" -Action inject_401
& "$PSScriptRoot\fault_injector.ps1" -Action inject_timeout
& "$PSScriptRoot\fault_injector.ps1" -Action inject_tool_fail

# 3. run drill
Write-Host ""
Write-Host "[3/5] Run fault drill..."
& "$PSScriptRoot\run_drill.ps1"

# 4. run eval
Write-Host ""
Write-Host "[4/5] Run evaluation..."
python "$PSScriptRoot\run_eval.py"
if ($LASTEXITCODE -ne 0) {
    Write-Warning " eval had issues, continuing to gate check..."
}

# 5. gate check
Write-Host ""
Write-Host "[5/5] Gate check..."
python "$PSScriptRoot\gate_check.py"
$gatePassed = $LASTEXITCODE -eq 0

# cleanup mock logs
$mockPaths = @(
    "$env:TEMP\openclaw_mock_401.log",
    "$env:TEMP\openclaw_mock_timeout.log",
    "$env:TEMP\openclaw_mock_tool_fail.log"
)
foreach ($p in $mockPaths) {
    if (Test-Path $p) { Remove-Item $p -Force }
}

Write-Host ""
Write-Host "========================================"
if ($gatePassed) {
    Write-Host " RESULT: ALL PASSED - gate check OK"
} else {
    Write-Host " RESULT: PIPELINE FINISHED - gate check FAILED"
    Write-Host " (this means protection is working)"
}
Write-Host " Backup: $backupPath"
Write-Host "========================================"
