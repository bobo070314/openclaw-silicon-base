param(
    [Parameter(Mandatory=$true)]
    [string]$CandidateConfig
)

$ACTIVE_CONFIG = Join-Path $PSScriptRoot ".." "configs" "active.yaml"
$BASE_PATH = Resolve-Path (Join-Path $PSScriptRoot "..")

Write-Host "[canary] Applying candidate: $CandidateConfig"
Copy-Item -Path $CandidateConfig -Destination $ACTIVE_CONFIG -Force
Write-Host "[canary] Traffic=5% Duration=60m"
Write-Host "[canary] Started at $(Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ')"
Write-Host "[canary] To promote: .\scripts\promote.ps1"
Write-Host "[canary] To rollback: .\scripts\rollback.ps1"
