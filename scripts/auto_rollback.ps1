#requires -version 5.1
<#
.SYNOPSIS
  Auto rollback script - triggered when gate_check.py returns non-zero.
  Restores last known good config, generates audit report, calls notify.

.PARAMETER RunId
  The run_id from the failed pipeline run.
.PARAMETER Trigger
  Description of what triggered the rollback (e.g. "gate_check FAIL: crash_rate too high")
.PARAMETER ConfigBackup
  Path to the config backup to restore. If empty, uses the latest backup.
.PARAMETER Violations
  Comma-separated list of violation descriptions.
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$RunId,

    [Parameter(Mandatory=$true)]
    [string]$Trigger,

    [Parameter(Mandatory=$false)]
    [string]$ConfigBackup = "",

    [Parameter(Mandatory=$false)]
    [string]$Violations = ""
)

$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$BASE_DIR = Split-Path -Parent $PSScriptRoot
$CONFIG_BACKUP_DIR = "$BASE_DIR\data\backups"
$REPORT_DIR = "$BASE_DIR\data\runs"
$ROLLBACK_REPORT_PATH = "$REPORT_DIR\rollback_report.json"
$POLICY_PATH = "$BASE_DIR\configs\rollback_policy.yaml"

Write-Host ""
Write-Host "=========================================="
Write-Host " AUTO_ROLLBACK: EXECUTED"
Write-Host "=========================================="

# 1. Load rollback policy
if (Test-Path $POLICY_PATH) {
    $policyRaw = Get-Content $POLICY_PATH -Raw -Encoding utf8
    $policyEnabled = $true
} else {
    Write-Host "[auto_rollback] WARN: rollback_policy.yaml not found, using defaults"
    $policyEnabled = $true
}

if (-not $policyEnabled) {
    Write-Host "[auto_rollback] rollback disabled by policy, skip"
    exit 0
}

# 2. Find config backup
if ([string]::IsNullOrEmpty($ConfigBackup)) {
    $latestBackup = Get-ChildItem -Path $CONFIG_BACKUP_DIR -Filter "openclaw-minimal.json.*.bak" `
        | Sort-Object LastWriteTime -Descending `
        | Select-Object -First 1
    if ($latestBackup) {
        $ConfigBackup = $latestBackup.FullName
    } else {
        Write-Host "[auto_rollback] WARN: no backup found, using default base config"
        $ConfigBackup = "$BASE_DIR\configs\base.yaml"
    }
}

Write-Host "[auto_rollback] restoring from: $ConfigBackup"

# 3. Restore config (rollback.ps1)
$rollbackResult = "SUCCESS"
$verifyResult = "SKIPPED"
try {
    & "$PSScriptRoot\rollback.ps1" -LastGood $ConfigBackup
    Write-Host "[auto_rollback] config restored OK"

    # 4. Verify the restored config
    & "$PSScriptRoot\rollback_verify.ps1" -BackupFile $ConfigBackup
    $verifyExitCode = $LASTEXITCODE
    # $? is false when Write-Error was called (even with Continue)
    # $LASTEXITCODE is more reliable
    if ($verifyExitCode -eq 0 -or $verifyExitCode -eq $null) {
        $verifyResult = "SUCCESS"
        Write-Host "[auto_rollback] verification passed"
    } else {
        $verifyResult = "WARN: verify check returned $verifyExitCode"
        Write-Host "[auto_rollback] WARN: verification returned exit code $verifyExitCode"
    }
} catch {
    $rollbackResult = "FAILED: $_"
    Write-Host "[auto_rollback] ERROR during restore: $_"
}

# 5. Generate rollback report
$violationsList = if ($Violations) { @($Violations -split "," | ForEach-Object { $_.Trim() }) } else { @() }

$report = @{
    timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
    run_id = $RunId
    trigger = $Trigger
    config_backup = $ConfigBackup
    rollback_status = $rollbackResult
    verify_status = $verifyResult
    violations = $violationsList
    pipeline_step = 6
}

$reportJson = $report | ConvertTo-Json -Depth 3
Set-Content -Path $ROLLBACK_REPORT_PATH -Value $reportJson -Encoding utf8
Write-Host "[auto_rollback] report saved: $ROLLBACK_REPORT_PATH"

# 6. Notify
& "$PSScriptRoot\notify.ps1" -ReportPath $ROLLBACK_REPORT_PATH -Mode rollback

Write-Host "=========================================="
Write-Host " AUTO_ROLLBACK: COMPLETE"
Write-Host "=========================================="
Write-Host ""
