param(
    [string]$Target = (Join-Path $PSScriptRoot ".." "configs" "active.yaml")
)

$BASE_CONFIG = Join-Path $PSScriptRoot ".." "configs" "base.yaml"

Write-Host "[promote] Promoting $Target to stable"
Copy-Item -Path $Target -Destination $BASE_CONFIG -Force
Write-Host "[promote] Done at $(Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ')"
