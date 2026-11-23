# RATGP one-click demo launcher (Windows PowerShell 5.1+ / PowerShell 7).
#
# Usage:
#   .\tools\demo.ps1              # backend(8000) + frontend(3000), open browser
#   .\tools\demo.ps1 -Reset       # rebuild demo data first (WARNING: wipes all projects)
#   .\tools\demo.ps1 -Dev         # use `next dev` instead of the production build
param(
    [int]$ApiPort = 8000,
    [int]$WebPort = 3000,
    [switch]$Reset,
    [switch]$Dev
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $root "venv\Scripts\python.exe"
$webDir = Join-Path $root "Web"

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
if (-not (Test-Path (Join-Path $webDir "node_modules"))) {
    throw "Web/node_modules not found. Run: cd Web; npm install"
}
if (Test-PortBusy $ApiPort) { throw "Port $ApiPort is busy. Stop the old backend first." }
if (Test-PortBusy $WebPort) { throw "Port $WebPort is busy. Stop the old frontend first." }

if ($Reset) {
    Write-Host "[demo] rebuilding demo data (all projects will be wiped)..." -ForegroundColor Yellow
    & $venvPython (Join-Path $root "tools\seed_demo.py") --yes
}

Write-Host "[demo] starting backend on $ApiPort ..." -ForegroundColor Cyan
Start-Process -FilePath $venvPython `
    -ArgumentList "-m", "uvicorn", "App.api.main:app", "--port", "$ApiPort" `
    -WorkingDirectory $root
if (-not (Wait-Http "http://127.0.0.1:$ApiPort/api/health" 45)) {
    throw "Backend did not become ready. Check the uvicorn window for errors."
}

if ($Dev) {
    Write-Host "[demo] starting frontend (dev) on $WebPort ..." -ForegroundColor Cyan
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "npm run dev" -WorkingDirectory $webDir
} else {
    $buildId = Join-Path $webDir ".next\BUILD_ID"
    if (-not (Test-Path $buildId)) {
        throw "Production build missing. Run: cd Web; npm run build   (or use -Dev)"
    }
    Write-Host "[demo] starting frontend (production) on $WebPort ..." -ForegroundColor Cyan
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "npx next start -p $WebPort" -WorkingDirectory $webDir
}

if (-not (Wait-Http "http://127.0.0.1:$WebPort" 120)) {
    throw "Frontend did not become ready. Check the frontend window."
}

Write-Host "[demo] opening browser ..." -ForegroundColor Green
Start-Process "http://127.0.0.1:$WebPort"

Write-Host ""
Write-Host "Ready:"
Write-Host "  App:  http://127.0.0.1:$WebPort"
Write-Host "  Docs: http://127.0.0.1:$ApiPort/docs"
Write-Host "Stop: close the two console windows it opened."
