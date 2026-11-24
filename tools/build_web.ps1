<#
.SYNOPSIS
    Build the Next.js client and copy the static export into .\web_dist.

.DESCRIPTION
    Pipeline for the single-process desktop build:

      1. verify Web\package.json and that next.config.* sets output: 'export'
      2. install dependencies when node_modules is missing
      3. npm run build inside Web\
      4. copy Web\out (Next static export) to <repo>\web_dist

    App/api/web_static.py (mount_web) serves web_dist from the same FastAPI
    process, so the desktop build never needs `next start` or a second process.

    Same-origin API note: the desktop backend listens on a random port, so the
    client must call relative /api/... URLs. Do NOT bake http://127.0.0.1:8000
    into a desktop build; use -ApiBase only for a fixed-port debug build.

.PARAMETER WebDir
    Next.js project directory. Default: <repo>\Web.

.PARAMETER OutDir
    Destination served by FastAPI. Default: <repo>\web_dist.

.PARAMETER SkipInstall
    Do not run npm install even when node_modules is missing.

.PARAMETER ApiBase
    Optional NEXT_PUBLIC_API_BASE baked into the build (e.g. http://127.0.0.1:8000
    for front-end debugging). Leave empty for a desktop build (same-origin).

.PARAMETER OutName
    Name of the Next static export directory. Default: out.

.PARAMETER UseExistingOut
    Skip the build and only copy an existing static export (Web\out).
    Useful when the front end was already built (CI) or Node is unavailable.

.PARAMETER Sandbox
    Force Web\scripts\build-sandbox.ps1 instead of `npm run build`. That script
    sets RATGP_BUILD_SANDBOX=1 and a NODE_OPTIONS patch so the Next.js build
    workers use worker_threads instead of child_process.fork. Required in the
    DSH sandbox (fork/pipes are blocked -> spawn EPERM) and in some CI images.
    Also selected automatically when DSH_* env vars are present or when
    `npm run build` fails with EPERM / DataCloneError.

.EXAMPLE
    .\tools\build_web.ps1

.EXAMPLE
    .\tools\build_web.ps1 -Sandbox

.EXAMPLE
    .\tools\build_web.ps1 -SkipInstall -ApiBase http://127.0.0.1:8000

.EXAMPLE
    .\tools\build_web.ps1 -UseExistingOut
#>
[CmdletBinding()]
param(
    [string]$WebDir,
    [string]$OutDir,
    [switch]$SkipInstall,
    [switch]$UseExistingOut,
    [switch]$Sandbox,
    [string]$ApiBase = "",
    [string]$OutName = "out"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
if (-not $WebDir) { $WebDir = Join-Path $repoRoot "Web" }
if (-not $OutDir) { $OutDir = Join-Path $repoRoot "build-artifacts\web_dist" }

$WebDir = [System.IO.Path]::GetFullPath($WebDir)
$OutDir = [System.IO.Path]::GetFullPath($OutDir)
$packageJson = Join-Path $WebDir "package.json"

if (-not (Test-Path -LiteralPath $packageJson -PathType Leaf)) {
    throw "Not a Next.js project (package.json missing): $WebDir"
}

# Guard against wiping the repo, the web sources, or a drive root.
$rootOfOut = [System.IO.Path]::GetPathRoot($OutDir)
$forbidden = @($WebDir, $repoRoot, $rootOfOut, (Join-Path $WebDir $OutName))
foreach ($item in $forbidden) {
    if ($item -and ([string]::Equals($OutDir, [System.IO.Path]::GetFullPath($item), [System.StringComparison]::OrdinalIgnoreCase))) {
        throw "Refusing to use OutDir=$OutDir (unsafe target)"
    }
}

# --- 1. next.config must enable static export -------------------------------
$nextConfig = Get-ChildItem -LiteralPath $WebDir -Filter "next.config.*" -File |
    Select-Object -First 1
if (-not $nextConfig) {
    throw "next.config.* not found in $WebDir"
}
$configText = Get-Content -LiteralPath $nextConfig.FullName -Raw
if ($configText -notmatch "output\s*:\s*['""]export['""]") {
    throw @"
$($nextConfig.Name) does not set output: 'export', so `next build` will not
produce a static export. The desktop build serves static files only.
Add it:
    const nextConfig: NextConfig = { output: 'export', /* ... */ };
See docs/封装说明.md (section 2).
"@
}
Write-Host "next.config    : $($nextConfig.FullName)"
Write-Host "static export  : $OutName"

# --- 2. node / npm / dependencies -------------------------------------------
$nodeModules = Join-Path $WebDir "node_modules"

if ($UseExistingOut) {
    $existing = Join-Path (Join-Path $WebDir $OutName) "index.html"
    if (-not (Test-Path -LiteralPath $existing -PathType Leaf)) {
        throw "UseExistingOut: no static export found at $(Join-Path $WebDir $OutName). Run a build first."
    }
    Write-Host "build          : skipped (-UseExistingOut)" -ForegroundColor Cyan
}
else {
    $npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if (-not $npmCommand) { $npmCommand = Get-Command npm -ErrorAction SilentlyContinue }
    if (-not $npmCommand) {
        throw "npm not found in PATH. Install Node.js 20+ (includes npm)."
    }

    if (-not (Test-Path -LiteralPath $nodeModules -PathType Container)) {
        if ($SkipInstall) { throw "node_modules missing and -SkipInstall was given: $nodeModules" }
        $lockFile = Join-Path $WebDir "package-lock.json"
        if (Test-Path -LiteralPath $lockFile -PathType Leaf) {
            Write-Host "Installing dependencies (npm ci)..." -ForegroundColor Cyan
            Push-Location $WebDir
            try { & $npmCommand.Source ci } finally { Pop-Location }
        }
        else {
            Write-Host "Installing dependencies (npm install)..." -ForegroundColor Cyan
            Push-Location $WebDir
            try { & $npmCommand.Source install } finally { Pop-Location }
        }
        if ($LASTEXITCODE -ne 0) { throw "npm install failed (exit $LASTEXITCODE)" }
    }

    # --- 3. build -----------------------------------------------------------
    $sandboxScript = Join-Path (Join-Path $WebDir "scripts") "build-sandbox.ps1"
    $sandboxAvailable = Test-Path -LiteralPath $sandboxScript -PathType Leaf
    $sandboxEnv = [bool]($env:DSH_HOME -or $env:DSH_SESSION_ID -or $env:DSH_PROFILE)
    $useSandbox = $Sandbox -or ($sandboxEnv -and $sandboxAvailable)

    if ($useSandbox) {
        if (-not $sandboxAvailable) {
            throw "Sandbox build requested but Web\scripts\build-sandbox.ps1 not found: $sandboxScript"
        }
        Write-Host "build          : Web\scripts\build-sandbox.ps1 (restricted environment)" -ForegroundColor Cyan
    }

    $previousApiBase = $env:NEXT_PUBLIC_API_BASE
    try {
        if ($ApiBase) {
            $env:NEXT_PUBLIC_API_BASE = $ApiBase
            Write-Host "API base       : $ApiBase (fixed, debug build)" -ForegroundColor Yellow
        }
        else {
            Remove-Item Env:NEXT_PUBLIC_API_BASE -ErrorAction SilentlyContinue
            Write-Host "API base       : same-origin /api/... (desktop build)"
        }

        if ($useSandbox) {
            & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $sandboxScript
            if ($LASTEXITCODE -ne 0) { throw "sandbox build failed (exit $LASTEXITCODE)" }
        }
        else {
            Write-Host "Running npm run build..." -ForegroundColor Cyan
            Push-Location $WebDir
            try {
                $buildOutput = & $npmCommand.Source run build *>&1 | Tee-Object -Variable buildOutput
            }
            finally { Pop-Location }
            $buildExit = $LASTEXITCODE

            if ($buildExit -ne 0) {
                $buildText = ($buildOutput | ForEach-Object { [string]$_ }) -join "`n"
                $restrictedError = $buildText -match "EPERM|DataCloneError|could not be cloned"
                if ($restrictedError -and $sandboxAvailable) {
                    Write-Warning ("npm run build hit a restricted-environment error " +
                        "(child_process.fork blocked: EPERM / DataCloneError). " +
                        "Retrying via Web\scripts\build-sandbox.ps1 ...")
                    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $sandboxScript
                    if ($LASTEXITCODE -ne 0) { throw "sandbox build failed (exit $LASTEXITCODE)" }
                }
                else {
                    throw "npm run build failed (exit $buildExit)"
                }
            }
        }
    }
    finally {
        if ($null -eq $previousApiBase) {
            Remove-Item Env:NEXT_PUBLIC_API_BASE -ErrorAction SilentlyContinue
        }
        else {
            $env:NEXT_PUBLIC_API_BASE = $previousApiBase
        }
    }
}

# --- 4. copy static export -> web_dist --------------------------------------
$source = Join-Path $WebDir $OutName
if (-not (Test-Path -LiteralPath $source -PathType Container)) {
    throw "Static export directory not found: $source (does next.config set output: 'export'?)"
}
$sourceIndex = Join-Path $source "index.html"
if (-not (Test-Path -LiteralPath $sourceIndex -PathType Leaf)) {
    throw "index.html missing from static export: $source"
}

if (Test-Path -LiteralPath $OutDir -PathType Container) {
    Remove-Item -LiteralPath $OutDir -Recurse -Force
}
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null

Get-ChildItem -LiteralPath $source -Force | Copy-Item -Destination $OutDir -Recurse -Force

if (-not (Test-Path -LiteralPath (Join-Path $OutDir "index.html") -PathType Leaf)) {
    throw "Copy failed: $OutDir\index.html missing"
}

$files = @(Get-ChildItem -LiteralPath $OutDir -Recurse -File)
$totalMb = [math]::Round((($files | Measure-Object -Property Length -Sum).Sum) / 1MB, 2)

# Warn when the fixed dev backend URL leaked into the desktop bundle.
if (-not $ApiBase) {
    $hardcoded = Get-ChildItem -LiteralPath (Join-Path $OutDir "_next") -Recurse -File -Filter "*.js" -ErrorAction SilentlyContinue |
        Select-String -Pattern "127\.0\.0\.1:8000|localhost:8000" -SimpleMatch:$false -List
    if ($hardcoded) {
        Write-Warning ("Bundle still references a fixed backend (127.0.0.1:8000). " +
            "The desktop app uses a random port, so the client should use relative /api/... URLs. " +
            "Check Web/lib/api.ts.")
    }
}

Write-Host ""
Write-Host "Web build OK" -ForegroundColor Green
Write-Host "  export : $source"
Write-Host "  served : $OutDir"
Write-Host "  files  : $($files.Count) ($totalMb MB)"
Write-Host "  run    : python desktop.py"
Write-Host ""

exit 0
