<#
.SYNOPSIS
    Create a timestamped backup of the RATGP SQLite database.

.DESCRIPTION
    Copies <DataDir>\ratgp.db to <DataDir>\backups\ratgp-<timestamp>.db.
    If SQLite wrote pending transactions to ratgp.db-wal, that file is copied
    next to the backup as <backup>-wal, so the backup can be restored completely
    (put both files back together). For the safest copy, close RATGP first.

    Exit codes: 0 = success, 2 = database not found, 3 = copy failed.

.PARAMETER DataDir
    RATGP data directory. Default: $env:RATGP_DATA_DIR if set, otherwise
    %APPDATA%\RATGP (same default as desktop.py).

.PARAMETER DbPath
    Explicit database file; overrides DataDir.

.PARAMETER OutDir
    Backup directory. Default: <DataDir>\backups.

.PARAMETER Keep
    Keep only the newest N backups (0 = keep everything).

.EXAMPLE
    .\tools\backup.ps1

.EXAMPLE
    .\tools\backup.ps1 -DataDir D:\RATGP-data -Keep 20

.EXAMPLE
    .\tools\backup.ps1 -DbPath .\App\data\ratgp.db -OutDir .\backups
#>
[CmdletBinding()]
param(
    [string]$DataDir,
    [string]$DbPath,
    [string]$OutDir,
    [int]$Keep = 0
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-DefaultDataDir {
    if ($env:RATGP_DATA_DIR) { return $env:RATGP_DATA_DIR }
    if ($env:APPDATA) { return (Join-Path $env:APPDATA "RATGP") }
    return (Join-Path $HOME "RATGP")
}

if (-not $DataDir) { $DataDir = Get-DefaultDataDir }
if (-not $DbPath) { $DbPath = Join-Path $DataDir "ratgp.db" }
if (-not $OutDir) { $OutDir = Join-Path $DataDir "backups" }

if (-not (Test-Path -LiteralPath $DbPath -PathType Leaf)) {
    Write-Host "ERROR: database not found: $DbPath" -ForegroundColor Red
    Write-Host "       RATGP must run once before the database exists." -ForegroundColor Red
    Write-Host "       Use -DataDir or -DbPath to point at another location." -ForegroundColor Red
    exit 2
}

$DbPath = (Resolve-Path -LiteralPath $DbPath).Path
$OutDir = [System.IO.Path]::GetFullPath($OutDir)

try {
    if (-not (Test-Path -LiteralPath $OutDir -PathType Container)) {
        New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
    }

    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
    $target = Join-Path $OutDir ("ratgp-{0}.db" -f $timestamp)

    Copy-Item -LiteralPath $DbPath -Destination $target -Force

    # SQLite WAL: keep pending transactions with the backup instead of losing them.
    $wal = "$DbPath-wal"
    $walCopied = $false
    if ((Test-Path -LiteralPath $wal -PathType Leaf) -and ((Get-Item -LiteralPath $wal).Length -gt 0)) {
        Copy-Item -LiteralPath $wal -Destination "$target-wal" -Force
        $walCopied = $true
    }
}
catch {
    Write-Host "ERROR: backup failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 3
}

$backup = Get-Item -LiteralPath $target
$sizeMb = [math]::Round($backup.Length / 1MB, 2)
$kept = 0

if ($Keep -gt 0) {
    $all = @(Get-ChildItem -LiteralPath $OutDir -Filter "ratgp-*.db" -File |
        Sort-Object LastWriteTime -Descending)
    foreach ($old in ($all | Select-Object -Skip $Keep)) {
        Remove-Item -LiteralPath $old.FullName -Force
        if (Test-Path -LiteralPath "$($old.FullName)-wal") {
            Remove-Item -LiteralPath "$($old.FullName)-wal" -Force
        }
        $kept++
    }
}

Write-Host ""
Write-Host "RATGP database backup created" -ForegroundColor Green
Write-Host "  source : $DbPath"
Write-Host "  backup : $($backup.FullName)"
Write-Host "  size   : $sizeMb MB"
if ($walCopied) {
    Write-Host "  wal    : $target-wal (pending transactions, keep both files together)" -ForegroundColor Yellow
}
if ($kept -gt 0) {
    Write-Host "  pruned : $kept old backup(s), kept newest $Keep" -ForegroundColor DarkGray
}
Write-Host ""

exit 0
