#requires -version 5.1
<#
.SYNOPSIS
  Notify script - prints rollback audit info to console (future: Slack/Flybook/Webhook)
.PARAMETER ReportPath
  Path to rollback_report.json
.PARAMETER Mode
  "rollback" or "skip"
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$ReportPath,

    [Parameter(Mandatory=$true)]
    [ValidateSet("rollback", "skip")]
    [string]$Mode
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

if ($Mode -eq "rollback") {
    if (-not (Test-Path $ReportPath)) {
        Write-Host "[notify] WARN: report not found at $ReportPath - printing what we have"
        return
    }

    $report = Get-Content $ReportPath -Raw | ConvertFrom-Json

    Write-Host ""
    Write-Host "=========================================="
    Write-Host " NOTIFICATION: Rollback Executed"
    Write-Host "=========================================="
    Write-Host "  Triggered at:  $($report.timestamp)"
    Write-Host "  Run ID:        $($report.run_id)"
    Write-Host "  Trigger:       $($report.trigger)"
    Write-Host "  Config backup: $($report.config_backup)"
    Write-Host "  Rollback:      $($report.rollback_status)"
    Write-Host "  Verify:        $($report.verify_status)"
    if ($report.violations) {
        Write-Host "  Violations:"
        foreach ($v in $report.violations) {
            Write-Host "    - $v"
        }
    }
    Write-Host "=========================================="
    Write-Host ""

} elseif ($Mode -eq "skip") {
    Write-Host ""
    Write-Host "=========================================="
    Write-Host " NOTIFICATION: Rollback Skipped"
    Write-Host "=========================================="
    Write-Host "  Gate check PASSED - no rollback needed"
    Write-Host "=========================================="
    Write-Host ""
}
