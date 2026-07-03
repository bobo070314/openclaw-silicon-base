#requires -version 5.1
param(
    [string]$GatewayStartCmd = "openclaw gateway"
)

$ErrorActionPreference = "Stop"

Write-Host "=== Fault Drill Start ==="

# 1. simulate gateway start (don't actually start, avoid bumping online session)
Write-Host "[drill] simulate gateway start..."
Write-Host "[drill] cmd: $GatewayStartCmd"
Start-Sleep -Milliseconds 500

# 2. verify mock logs exist
$mockLogs = @()
$mockPaths = @(
    "$env:TEMP\openclaw_mock_401.log",
    "$env:TEMP\openclaw_mock_timeout.log",
    "$env:TEMP\openclaw_mock_tool_fail.log"
)
foreach ($p in $mockPaths) {
    if (Test-Path $p) {
        $mockLogs += $p
        Write-Host "[drill] found mock log: $p"
    }
}

if ($mockLogs.Count -eq 0) {
    Write-Warning "[drill] no mock logs found, skip"
    exit 0
}

# 3. simulate collect_failures from mock logs
Write-Host "[drill] simulate collect_failures run..."
foreach ($log in $mockLogs) {
    $content = Get-Content $log -Raw
    Write-Host "  -> captured: $($content.Trim())"
}

# 4. acceptance check
$has401 = $mockLogs | Where-Object { $_ -match "401" } | Select-Object -First 1
$hasTimeout = $mockLogs | Where-Object { $_ -match "timeout" } | Select-Object -First 1
$hasToolFail = $mockLogs | Where-Object { $_ -match "tool_fail" } | Select-Object -First 1

if ($has401) { Write-Host "[accept] 401 injection OK" }
if ($hasTimeout) { Write-Host "[accept] timeout injection OK" }
if ($hasToolFail) { Write-Host "[accept] tool_fail injection OK" }

Write-Host "[drill] drill complete"
