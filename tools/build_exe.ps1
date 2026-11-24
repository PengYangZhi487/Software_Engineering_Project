<#
.SYNOPSIS
    Package RATGP into a Windows desktop executable with PyInstaller.

.DESCRIPTION
    Prerequisites
      * .\web_dist built first:   .\tools\build_web.ps1
      * a Python environment with App\requirements.txt, pywebview and pyinstaller:
            python -m pip install -r App\requirements.txt
            python -m pip install pywebview pyinstaller
      * WebView2 Runtime (Edge). Preinstalled on Windows 10/11; otherwise ship
        https://developer.microsoft.com/microsoft-edge/webview2/

    Why these PyInstaller options (hidden imports / collections):

      --collect-submodules App
            The API layer imports routers/services by module path; collecting the
            whole package keeps App.api.routers.*, App.dao.*, App.services.* inside
            the frozen app even where imports are indirect.

      --collect-submodules uvicorn
            uvicorn resolves its loop / HTTP / WebSocket implementations at
            runtime (uvicorn.loops.auto, uvicorn.protocols.http.auto,
            uvicorn.protocols.http.h11_impl, uvicorn.lifespan.on, ...).
            Static analysis cannot see them, so the app dies with
            "Could not import module ..." without these.

      --collect-all webview + --hidden-import clr
            On Windows pywebview uses the EdgeChromium backend through
            pythonnet (clr) and picks a GUI toolkit (winforms) at runtime.
            --collect-all webview ships webview.platforms.* and its data files;
            clr is a native CPython extension that PyInstaller only finds via
            an explicit hidden import.

      --add-data "web_dist;web_dist"
            App/api/web_static.py also looks in sys._MEIPASS\web_dist, which is
            where onefile builds unpack this data.

      --windowed
            No console window in production. Pass -Console for a build that
            keeps the console (useful when debugging a frozen app).

    Output: dist\<Name>.exe (onefile by default) or dist\<Name>\ (with -OneDir).

.PARAMETER Python
    Python interpreter used for the build. Default: $env:RATGP_PYTHON, then
    <repo>\venv\Scripts\python.exe, then "python" from PATH.

.PARAMETER Name
    Executable / app name. Default: RATGP.

.PARAMETER OneDir
    Build a folder (--onedir) instead of a single .exe. Starts faster.

.PARAMETER Console
    Keep a console window (--console), for debugging the packaged app.

.PARAMETER CleanOutputs
    Remove dist\ and build\ before packaging.

.PARAMETER DryRun
    Print the PyInstaller command without running it.

.EXAMPLE
    .\tools\build_exe.ps1

.EXAMPLE
    .\tools\build_exe.ps1 -Python C:\Python312\python.exe -OneDir -Console
#>
[CmdletBinding()]
param(
    [string]$Python,
    [string]$Name = "RATGP",
    [switch]$OneDir,
    [switch]$Console,
    [switch]$CleanOutputs,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

# --- 1. web_dist must exist ------------------------------------------------
$webDist = Join-Path $repoRoot "web_dist"
if (-not (Test-Path -LiteralPath (Join-Path $webDist "index.html") -PathType Leaf)) {
    throw "web_dist\index.html not found. Run .\tools\build_web.ps1 first."
}

# --- 2. resolve Python -----------------------------------------------------
function Resolve-Python {
    if ($env:RATGP_PYTHON) { return $env:RATGP_PYTHON }
    $venv = Join-Path $repoRoot "venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $venv -PathType Leaf) { return $venv }
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

if (-not $Python) { $Python = Resolve-Python }
if (-not $Python) {
    throw "Python not found. Pass -Python <path> or set RATGP_PYTHON."
}
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "Python interpreter not found: $Python"
}
Write-Host "python         : $Python"

$version = & $Python -c "import sys; print(sys.version.split()[0])" 2>$null
Write-Host "version        : $version"

# --- 3. PyInstaller available? --------------------------------------------
$hasPyInstaller = $false
try {
    & $Python -c "import PyInstaller; print(PyInstaller.__version__)" 2>$null | Out-Null
    $hasPyInstaller = ($LASTEXITCODE -eq 0)
}
catch {
    $hasPyInstaller = $false
}
if (-not $hasPyInstaller) {
    if ($DryRun) {
        Write-Warning "PyInstaller is not installed in this interpreter; dry run only."
    }
    else {
        throw @"
PyInstaller is not installed in this interpreter. Install the build tools:
    & '$Python' -m pip install pyinstaller pywebview
"@
    }
}

# --- 4. optional clean -----------------------------------------------------
$distPath = Join-Path $repoRoot "dist"
$buildPath = Join-Path $repoRoot "build"
if ($CleanOutputs) {
    foreach ($path in @($distPath, $buildPath)) {
        if (Test-Path -LiteralPath $path -PathType Container) {
            Remove-Item -LiteralPath $path -Recurse -Force
            Write-Host "removed        : $path"
        }
    }
}

# --- 5. assemble the command ----------------------------------------------
$mode = if ($OneDir) { "--onedir" } else { "--onefile" }
$windowMode = if ($Console) { "--console" } else { "--windowed" }

$arguments = @(
    "-m", "PyInstaller",
    "--noconfirm", "--clean",
    "--name", $Name,
    $mode,
    $windowMode,
    "--add-data", "web_dist;web_dist",
    "--collect-submodules", "App",
    "--collect-submodules", "uvicorn",
    "--collect-all", "webview",
    "--hidden-import", "clr",
    "--hidden-import", "uvicorn.logging",
    "--hidden-import", "uvicorn.loops.auto",
    "--hidden-import", "uvicorn.loops.asyncio",
    "--hidden-import", "uvicorn.protocols.http.auto",
    "--hidden-import", "uvicorn.protocols.http.h11_impl",
    "--hidden-import", "uvicorn.protocols.websockets.auto",
    "--hidden-import", "uvicorn.lifespan.on",
    "--distpath", $distPath,
    "--workpath", $buildPath,
    "--specpath", $repoRoot,
    (Join-Path $repoRoot "desktop.py")
)

Write-Host ""
Write-Host "PyInstaller command:" -ForegroundColor Cyan
Write-Host ("  & '{0}' {1}" -f $Python, ($arguments -join " "))
Write-Host ""

if ($DryRun) {
    Write-Host "Dry run only; nothing was built." -ForegroundColor Yellow
    exit 0
}

Push-Location $repoRoot
try {
    & $Python @arguments
}
finally {
    Pop-Location
}
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed (exit $LASTEXITCODE). See build\ for logs."
}

$artifact = if ($OneDir) { Join-Path $distPath $Name } else { Join-Path $distPath "$Name.exe" }
if (-not (Test-Path -LiteralPath $artifact)) {
    throw "Build finished but artifact not found: $artifact"
}

Write-Host ""
Write-Host "Desktop build OK" -ForegroundColor Green
Write-Host "  artifact : $artifact"
Write-Host "  data dir : %APPDATA%\RATGP (created on first run)"
Write-Host "  smoke    : `"$artifact`" --no-window --port 8123 --exit-after 5"
Write-Host ""

exit 0
