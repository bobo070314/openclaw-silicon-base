# run_all.ps1 - 一键执行全链路演练
param(
    [switch]$SkipFaultInjection
)

$ErrorActionPreference = "Continue"
$CONFIG_BACKUP_PATH = "D:\bobo\openclaw-foreign\openclaw-minimal.json"
$BASE_DIR = Split-Path -Parent $PSScriptRoot

Write-Host "`n========================================"
Write-Host "   硅基体集团 MVP 全链路演练"
Write-Host "========================================"

# 1. 先备份当前配置
Write-Host "`n[1/5] 备份当前配置..."
$BACKUP_DIR = Join-Path $BASE_DIR "data" "backups"
if (-not (Test-Path $BACKUP_DIR)) { New-Item -ItemType Directory -Path $BACKUP_DIR -Force | Out-Null }
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupPath = Join-Path $BACKUP_DIR "openclaw-minimal.json.$timestamp.bak"
Copy-Item -Path $CONFIG_BACKUP_PATH -Destination $backupPath -Force
Write-Host "  ✅ 已备份到: $backupPath"

# 2. 故障注入（可选跳过）
if (-not $SkipFaultInjection) {
    Write-Host "`n[2/5] 注入故障..."
    & "$PSScriptRoot\fault_injector.ps1" -Action inject_401
    & "$PSScriptRoot\fault_injector.ps1" -Action inject_timeout
    & "$PSScriptRoot\fault_injector.ps1" -Action inject_tool_fail
} else {
    Write-Host "`n[2/5] 跳过故障注入"
}

# 3. 运行演练
Write-Host "`n[3/5] 运行故障演练..."
& "$PSScriptRoot\run_drill.ps1"

# 4. 运行评测
Write-Host "`n[4/5] 运行评测..."
python "$PSScriptRoot\run_eval.py"
if ($LASTEXITCODE -ne 0) {
    Write-Warning "  ⚠️ 评测有异常，继续执行门禁..."
}

# 5. 门禁检查
Write-Host "`n[5/5] 门禁检查..."
python "$PSScriptRoot\gate_check.py"
$gatePassed = $LASTEXITCODE -eq 0

# 清理 mock 日志
$mockPaths = @(
    "$env:TEMP\openclaw_mock_401.log",
    "$env:TEMP\openclaw_mock_timeout.log",
    "$env:TEMP\openclaw_mock_tool_fail.log"
)
foreach ($p in $mockPaths) {
    if (Test-Path $p) { Remove-Item $p -Force }
}

Write-Host "`n========================================"
if ($gatePassed) {
    Write-Host "  ✅ 全链路演练通过！门禁通过"
} else {
    Write-Host "  ⚠️ 演练完成，门禁未通过"
    Write-Host "  建议：调整 hardcases.jsonl 或 guardrails.yaml 阈值后重试"
}
Write-Host "========================================"
Write-Host "备份保留: $backupPath"
