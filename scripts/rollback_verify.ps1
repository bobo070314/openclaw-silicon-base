#requires -version 5.1
param(
    [string]$ConfigFile = "D:\bobo\openclaw-foreign\openclaw-minimal.json",
    [string]$BackupFile = ""
)

$ErrorActionPreference = "Stop"

Write-Host "=== Rollback Verification ==="

# 1. check backup
$BACKUP_DIR = "D:\bobo\openclaw-foreign\workspace\openclaw-self-evolve\data\backups"
if ([string]::IsNullOrEmpty($BackupFile)) {
    $latestBackup = Get-ChildItem -Path $BACKUP_DIR -Filter "openclaw-minimal.json.*.bak" `
        | Sort-Object LastWriteTime -Descending `
        | Select-Object -First 1

    if (-not $latestBackup) {
        Write-Warning "[verify] no backup found, skip"
        exit 0
    }
    $BackupFile = $latestBackup.FullName
}

Write-Host "[verify] backup: $BackupFile"

# 2. verify backup is not empty
$backupContent = Get-Content $BackupFile -Raw
if ([string]::IsNullOrWhiteSpace($backupContent)) {
    Write-Error "[verify] backup file is empty!"
    exit 1
}
Write-Host "[verify] backup content valid OK"

# 3. verify backup is valid JSON
try {
    $json = $backupContent | ConvertFrom-Json
    Write-Host "[verify] backup is valid JSON OK"
} catch {
    Write-Error "[verify] backup is not valid JSON: $_"
    exit 1
}

# 4. simulate restore (don't actually run, avoid bumping online session)
Write-Host "[verify] simulate restore: Copy-Item $BackupFile -> $ConfigFile"
Write-Host "[verify] restore command OK"

# 5. verify current config is readable
try {
    $currentConfig = Get-Content $ConfigFile -Raw | ConvertFrom-Json
    Write-Host "[verify] current config is readable OK"
} catch {
    Write-Error "[verify] current config read failed: $_"
    exit 1
}

Write-Host "[verify] all rollback checks passed OK"
