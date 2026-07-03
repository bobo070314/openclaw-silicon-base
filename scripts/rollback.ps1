param(
    [string]$LastGood = ""
)

$BASE = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrEmpty($LastGood)) {
    $LastGood = Join-Path $BASE "configs\base.yaml"
}

$ACTIVE_CONFIG = Join-Path $BASE "configs\active.yaml"

Write-Host "[rollback] Restoring $LastGood -> $ACTIVE_CONFIG"
Copy-Item -Path $LastGood -Destination $ACTIVE_CONFIG -Force
Write-Host "[rollback] Completed at $(Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ')"
