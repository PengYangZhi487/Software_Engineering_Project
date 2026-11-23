# RATGP one-click demo launcher (Windows PowerShell 5.1+ / PowerShell 7).
#
# Default is dev mode (same as `npm run dev`, no production build needed).
#
# Usage:
#   .\tools\demo.ps1              # dev mode: backend(8000) + frontend(3000), open browser
#   .\tools\demo.ps1 -Prod        # production mode (runs `next build` first if missing)
#   .\tools\demo.ps1 -Reset       # rebuild demo data first (WARNING: wipes all projects)
param(
    [int]$ApiPort = 8000,
    [int]$WebPort = 3000,
    [switch]$Reset,
    [switch]$Prod
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $root "venv\Scripts\python.exe"
$webDir = Join-Path $root "Web"
$nextCmd = Join-Path $webDir "node_modules\.bin\next.cmd"
$logDir = Join-Path $root "App\data"
$apiLog = Join-Path $logDir "demo-api.log"
$webLog = Join-Path $logDir "demo-web.log"

function Test-PortBusy([int]$port) {
    $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    return [bool]$conn
}

function Wait-Http([string]$url, [int]$timeoutSec) {
    $deadline = (Get-Date).AddSeconds($timeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $resp = Invoke-WebRequest -Uri $url -TimeoutSec 2 -UseBasicParsing
            if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500) { return $true }
        } catch {
            Start-Sleep -Milliseconds 600
        }
    }
    return $false
}

if (-not (Test-Path $venvPython)) { throw "venv not found: $venvPython" }
if (-not (Test-Path $nextCmd)) {
    throw "Web/node_modules not found. Run: cd Web; npm install"
}
if (Test-PortBusy $ApiPort) { throw "Port $ApiPort is busy. Stop the old backend first." }
if (Test-PortBusy $WebPort) { throw "Port $WebPort is busy. Stop the old frontend first." }

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

if ($Reset) {
    Write-Host "[demo] rebuilding demo data (all projects will be wiped)..." -ForegroundColor Yellow
    & $venvPython (Join-Path $root "tools\seed_demo.py") --yes
}

Write-Host "[demo] starting backend on $ApiPort ..." -ForegroundColor Cyan
$apiCmd = "title RATGP-backend & `"$venvPython`" -X utf8 -m uvicorn App.api.main:app --port $ApiPort > `"$apiLog`" 2>&1"
Start-Process -FilePath "cmd.exe" -ArgumentList "/c", $apiCmd -WorkingDirectory $root

if (-not (Wait-Http "http://127.0.0.1:$ApiPort/api/health" 60)) {
    Write-Host "[demo] backend did not become ready. Last log lines:" -ForegroundColor Red
    if (Test-Path $apiLog) { Get-Content $apiLog -Tail 20 }
    throw "Backend failed to start. Log: $apiLog"
}

if ($Prod) {
    if (-not (Test-Path (Join-Path $webDir ".next\BUILD_ID"))) {
        Write-Host "[demo] production build missing, running next build ..." -ForegroundColor Yellow
        Push-Location $webDir
        try { & $nextCmd build } finally { Pop-Location }
    }
    Write-Host "[demo] starting frontend (production) on $WebPort ..." -ForegroundColor Cyan
    $webCmd = "title RATGP-web & `"$nextCmd`" start -p $WebPort > `"$webLog`" 2>&1"
} else {
    Write-Host "[demo] starting frontend (dev) on $WebPort ..." -ForegroundColor Cyan
    $webCmd = "title RATGP-web & `"$nextCmd`" dev -p $WebPort > `"$webLog`" 2>&1"
}
Start-Process -FilePath "cmd.exe" -ArgumentList "/c", $webCmd -WorkingDirectory $webDir

if (-not (Wait-Http "http://127.0.0.1:$WebPort" 180)) {
    Write-Host "[demo] frontend did not become ready. Last log lines:" -ForegroundColor Red
    if (Test-Path $webLog) { Get-Content $webLog -Tail 25 }
    throw "Frontend failed to start. Log: $webLog"
}

Write-Host "[demo] opening browser ..." -ForegroundColor Green
Start-Process "http://127.0.0.1:$WebPort"

Write-Host ""
Write-Host "Ready:"
Write-Host "  App:  http://127.0.0.1:$WebPort"
Write-Host "  Docs: http://127.0.0.1:$ApiPort/docs"
Write-Host "  Mode: $(if ($Prod) { 'production' } else { 'dev' })"
Write-Host "  Logs: $apiLog  |  $webLog"
Write-Host ""
Write-Host "IMPORTANT: keep the two console windows (RATGP-backend / RATGP-web) open."
Write-Host "Close them to stop the demo."
