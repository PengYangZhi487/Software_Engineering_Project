# Build for restricted environments (DSH sandbox / CI where child_process.fork is blocked).
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build-sandbox.ps1
#
# RATGP_BUILD_SANDBOX=1 switches next.config.ts build workers to worker_threads (no fork),
# and NODE_OPTIONS loads sandbox-worker-patch.cjs to strip Next's default function fields
# before they are structured-cloned. Output is the same static export (out/).
#
# Normal dev / packaging machines do not need this: just run `npm run build`.

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$web = Split-Path -Parent $here

# NODE_OPTIONS needs forward slashes: backslashes are eaten by Node's option parser
$patch = (Join-Path $here "sandbox-worker-patch.cjs") -replace '\\', '/'

$env:RATGP_BUILD_SANDBOX = "1"
$env:NEXT_TELEMETRY_DISABLED = "1"
$prevNodeOptions = $env:NODE_OPTIONS
$env:NODE_OPTIONS = (($prevNodeOptions, "--require $patch") -join " ").Trim()

Push-Location $web
try {
    & ".\node_modules\.bin\next.cmd" build
    exit $LASTEXITCODE
}
finally {
    Pop-Location
    $env:NODE_OPTIONS = $prevNodeOptions
    Remove-Item Env:\RATGP_BUILD_SANDBOX -ErrorAction SilentlyContinue
}
