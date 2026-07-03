#requires -version 5.1
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("backup","inject_401","inject_timeout","inject_tool_fail","restore")]
    [string]$Action
)

$BASE_DIR = Split-Path -Parent $PSScriptRoot
$CONFIG_FILE = "D:\bobo\openclaw-foreign\openclaw-minimal.json"
$BACKUP_DIR = "$BASE_DIR\data\backups"
$TIMESTAMP = Get-Date -Format "yyyyMMdd_HHmmss"

switch ($Action) {
    "backup" {
        if (-not (Test-Path $BACKUP_DIR)) { New-Item -ItemType Directory -Path $BACKUP_DIR -Force | Out-Null }
        $backupPath = "$BACKUP_DIR\openclaw-minimal.json.$TIMESTAMP.bak"
        Copy-Item -Path $CONFIG_FILE -Destination $backupPath -Force
        Write-Host "[backup] saved: $backupPath"
    }
    "inject_401" {
        Write-Host "[inject] inject 401 fault (siliconflow key expired)"
        $mockLogPath = "$env:TEMP\openclaw_mock_401.log"
        "[mock 401] provider auth state pre-warmed returned 401 for siliconflow" | Out-File -FilePath $mockLogPath -Encoding utf8
        Write-Host "[inject] mock log: $mockLogPath"
    }
    "inject_timeout" {
        Write-Host "[inject] inject timeout fault (siliconflow request timeout)"
        $mockLogPath = "$env:TEMP\openclaw_mock_timeout.log"
        "[mock timeout] siliconflow request timed out after 30000ms" | Out-File -FilePath $mockLogPath -Encoding utf8
        Write-Host "[inject] mock log: $mockLogPath"
    }
    "inject_tool_fail" {
        Write-Host "[inject] inject tool failure (fixer patch validation failed)"
        $mockLogPath = "$env:TEMP\openclaw_mock_tool_fail.log"
        "[mock tool_fail] fixer agent patch validation failed: unit test not passing" | Out-File -FilePath $mockLogPath -Encoding utf8
        Write-Host "[inject] mock log: $mockLogPath"
    }
    "restore" {
        $latestBackup = Get-ChildItem -Path $BACKUP_DIR -Filter "openclaw-minimal.json.*.bak" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($latestBackup) {
            Copy-Item -Path $latestBackup.FullName -Destination $CONFIG_FILE -Force
            Write-Host "[restore] restored from $($latestBackup.Name)"
        } else {
            Write-Warning "[restore] no backup found"
        }
    }
}
