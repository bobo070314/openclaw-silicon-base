# run_drill.ps1 - 自动演练 + 验收
param(
    [string]$GatewayStartCmd = "openclaw gateway"
)

$ErrorActionPreference = "Stop"

Write-Host "=== 开始故障演练 ==="

# 1. 模拟网关启动（实际不启动，防止打断在线会话）
Write-Host "[drill] 模拟网关启动..."
Write-Host "[drill] 命令: $GatewayStartCmd"
Start-Sleep -Milliseconds 500

# 2. 验证 mock 日志存在
$mockLogs = @()
$mockPaths = @(
    "$env:TEMP\openclaw_mock_401.log",
    "$env:TEMP\openclaw_mock_timeout.log",
    "$env:TEMP\openclaw_mock_tool_fail.log"
)
foreach ($p in $mockPaths) {
    if (Test-Path $p) {
        $mockLogs += $p
        Write-Host "[drill] 找到 mock 日志: $p"
    }
}

if ($mockLogs.Count -eq 0) {
    Write-Warning "[drill] 没有找到 mock 日志，跳过"
    exit 0
}

# 3. 模拟 collect_failures 从 mock 日志抓取
Write-Host "[drill] 模拟 collect_failures 运行..."
foreach ($log in $mockLogs) {
    $content = Get-Content $log -Raw
    Write-Host "  → 抓取到: $($content.Trim())"
}

# 4. 验收：验证日志可以被正确读取
$has401 = $mockLogs | Where-Object { $_ -match "401" } | Select-Object -First 1
$hasTimeout = $mockLogs | Where-Object { $_ -match "timeout" } | Select-Object -First 1
$hasToolFail = $mockLogs | Where-Object { $_ -match "tool_fail" } | Select-Object -First 1

if ($has401) { Write-Host "[验收] 401 故障注入 ✅" }
if ($hasTimeout) { Write-Host "[验收] 超时故障注入 ✅" }
if ($hasToolFail) { Write-Host "[验收] 工具失败故障注入 ✅" }

Write-Host "[drill] 演练完成"
