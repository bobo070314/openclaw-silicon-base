param(
    [string]$MetricFile = (Join-Path $PSScriptRoot ".." "data" "runs" "latest_eval.json")
)

$ResolvedMetricFile = Resolve-Path $MetricFile -ErrorAction SilentlyContinue

if (-not $ResolvedMetricFile) {
    Write-Error "Metric file not found: $MetricFile"
    exit 2
}

$m = Get-Content $ResolvedMetricFile | ConvertFrom-Json
$ok = $true

function Check([string]$Name, [double]$Val, [string]$Op, [double]$Th) {
    $passed = if ($Op -eq "<=") { $Val -le $Th } else { $Val -ge $Th }
    $status = if ($passed) { "PASS" } else { "FAIL" }
    Write-Host "  $status | $Name`: $Val (threshold $Op $Th)"
    if (-not $passed) { $script:ok = $false }
}

Write-Host "=== Health Check ==="
Check "pass_rate" $m.pass_rate ">=" 0.88
Check "login_redirect_rate" $m.login_redirect_rate "<=" 0.003
Check "crash_rate" $m.crash_rate "<=" 0.005
Check "p95_latency_ms" $m.p95_latency_ms "<=" 9000

if ($ok) {
    Write-Host "`n✅ Health check PASSED"
    exit 0
} else {
    Write-Host "`n❌ Health check FAILED"
    exit 1
}
