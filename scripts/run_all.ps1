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
Write-Host "[1/7] Backup config..."
$BACKUP_DIR = "$BASE_DIR\data\backups"
if (-not (Test-Path $BACKUP_DIR)) { New-Item -ItemType Directory -Path $BACKUP_DIR -Force | Out-Null }
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupPath = "$BACKUP_DIR\openclaw-minimal.json.$timestamp.bak"
Copy-Item -Path $CONFIG_BACKUP_PATH -Destination $backupPath -Force
Write-Host " -> backup saved: $backupPath"

# 2. fault injection
Write-Host ""
Write-Host "[2/7] Inject faults..."
& "$PSScriptRoot\fault_injector.ps1" -Action inject_401
& "$PSScriptRoot\fault_injector.ps1" -Action inject_timeout
& "$PSScriptRoot\fault_injector.ps1" -Action inject_tool_fail

# 3. RBAC permission check
Write-Host ""
Write-Host "[3/7] RBAC permission check..."
$CHANGED_FILES = "$BASE_DIR\data\runs\changed_files.json"
if (Test-Path $CHANGED_FILES) {
    $rbacRole = if ($env:RBAC_ROLE) { $env:RBAC_ROLE } else { "CEO" }
    python "$PSScriptRoot\permission_check.py" --role $rbacRole --changed-files $CHANGED_FILES
    $permPassed = $LASTEXITCODE -eq 0
} else {
    Write-Host " -> no changed_files.json found, skipping RBAC check"
    $permPassed = $true
}

# 4. run drill
Write-Host ""
Write-Host "[4/7] Run fault drill..."
& "$PSScriptRoot\run_drill.ps1"

# 5. run eval
Write-Host ""
Write-Host "[5/7] Run evaluation..."
python "$PSScriptRoot\run_eval.py"
if ($LASTEXITCODE -ne 0) {
    Write-Warning " eval had issues, continuing to gate check..."
}

# 6. gate check
Write-Host ""
Write-Host "[6/7] Gate check..."
python "$PSScriptRoot\gate_check.py"
$gatePassed = $LASTEXITCODE -eq 0

# 7. auto rollback decision
Write-Host ""
Write-Host "[7/7] Auto rollback decision..."
$runId = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
$anyFailed = (-not $permPassed) -or (-not $gatePassed)

if ($anyFailed) {
    $violations = @()
    if (-not $permPassed) { $violations += "permission_gate: role blocked" }
    if (-not $gatePassed) { $violations += "gate_check: quality gate blocked" }
    $violationsStr = $violations -join ","

    & "$PSScriptRoot\auto_rollback.ps1" `
        -RunId $runId `
        -Trigger "pipeline gate FAIL (perm=$permPassed, gate=$gatePassed)" `
        -ConfigBackup $backupPath `
        -Violations $violationsStr
    # PR comment (only on failure)
    $prNumber = $env:PR_NUMBER
    if ($prNumber) {
        Write-Host ""
        Write-Host "[BONUS] Posting PR comment..."
        python "$PSScriptRoot\comment_on_pr.py" --pr $prNumber
        if ($LASTEXITCODE -eq 0) {
            Write-Host " -> PR comment posted"
        } else {
            Write-Warning " -> PR comment failed (exit $LASTEXITCODE)"
        }
    } else {
        Write-Host ""
        Write-Host "[BONUS] No PR_NUMBER set, skipping PR comment"
    }
} else {
    Write-Host "AUTO_ROLLBACK: SKIPPED (all gates passed)"
    & "$PSScriptRoot\notify.ps1" -ReportPath "" -Mode skip
}

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
if ($permPassed -and $gatePassed) {
    Write-Host " RESULT: ALL PASSED - RBAC + gate check OK"
    Write-Host " AUTO_ROLLBACK: SKIPPED"
} else {
    Write-Host " RESULT: PIPELINE FINISHED - rollback executed"
    if (-not $permPassed) { Write-Host " permission_gate: FAIL" }
    if (-not $gatePassed) { Write-Host " gate_check: FAIL" }
    Write-Host " AUTO_ROLLBACK: EXECUTED"
}
Write-Host " Backup: $backupPath"
Write-Host "========================================"
