param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("backup","inject_401","inject_timeout","inject_tool_fail","restore")]
    [string]$Action
)

$BASE_DIR = Split-Path -Parent $PSScriptRoot
$CONFIG_FILE = "D:\bobo\openclaw-foreign\openclaw-minimal.json"
$BACKUP_DIR = Join-Path $BASE_DIR "data" "backups"
$TIMESTAMP = Get-Date -Format "yyyyMMdd_HHmmss"

switch ($Action) {
    "backup" {
        if (-not (Test-Path $BACKUP_DIR)) { New-Item -ItemType Directory -Path $BACKUP_DIR -Force | Out-Null }
        $backupPath = Join-Path $BACKUP_DIR "openclaw-minimal.json.$TIMESTAMP.bak"
        Copy-Item -Path $CONFIG_FILE -Destination $backupPath -Force
        Write-Host "[backup] 已备份到: $backupPath"
    }
    "inject_401" {
        Write-Host "[inject] 注入 401 故障：模拟硅基流动 Key 过期"
        Write-Host "[inject] 方式：在日志中写入 mock 401 错误（不碰真实配置）"
        # 实际不会改 openclaw-minimal.json，只写一条 mock 日志
        $mockLogPath = "$env:TEMP\openclaw_mock_401.log"
        "[mock 401] provider auth state pre-warmed returned 401 for siliconflow" | Out-File -FilePath $mockLogPath -Encoding utf8
        Write-Host "[inject] mock 401 日志已写入: $mockLogPath"
    }
    "inject_timeout" {
        Write-Host "[inject] 注入超时故障：模拟硅基流动请求超时"
        $mockLogPath = "$env:TEMP\openclaw_mock_timeout.log"
        "[mock timeout] siliconflow request timed out after 30000ms" | Out-File -FilePath $mockLogPath -Encoding utf8
        Write-Host "[inject] mock timeout 日志已写入: $mockLogPath"
    }
    "inject_tool_fail" {
        Write-Host "[inject] 注入工具失败：模拟 Fixer Agent 补丁测试失败"
        $mockLogPath = "$env:TEMP\openclaw_mock_tool_fail.log"
        "[mock tool_fail] Fixer agent patch validation failed: unit test not passing" | Out-File -FilePath $mockLogPath -Encoding utf8
        Write-Host "[inject] mock tool_fail 日志已写入: $mockLogPath"
    }
    "restore" {
        $latestBackup = Get-ChildItem -Path $BACKUP_DIR -Filter "openclaw-minimal.json.*.bak" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($latestBackup) {
            Copy-Item -Path $latestBackup.FullName -Destination $CONFIG_FILE -Force
            Write-Host "[restore] 已从 $($latestBackup.Name) 恢复配置"
        } else {
            Write-Warning "[restore] 没有找到备份文件"
        }
    }
}
