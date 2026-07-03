param(
    [string]$LastGood = (Join-Path $PSScriptRoot ".." "configs" "base.yaml")
)

$ACTIVE_CONFIG = Join-Path $PSScriptRoot ".." "configs" "active.yaml"

Write-Host "[rollback] Restoring $LastGood -> $ACTIVE_CONFIG"
Copy-Item -Path $LastGood -Destination $ACTIVE_CONFIG -Force
Write-Host "[rollback] Completed at $(Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ')"
