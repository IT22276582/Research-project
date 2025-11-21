Param(
    [switch] $WithHooks
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$pyDir = Join-Path $root "."
$venv = Join-Path $pyDir ".venv\\Scripts"
$backendExe = Join-Path $venv "cog-py-est.exe"
$hookExe = Join-Path $venv "cle-os-hooks.exe"
$uiDir = Join-Path $pyDir "web-ui"

if (-not (Test-Path $backendExe)) {
    Write-Error "Backend not found. Run 'python -m venv .venv' and 'python -m pip install .[hooks]' in cog_py_est first."
}

if (-not (Test-Path (Join-Path $uiDir "node_modules"))) {
    Write-Output "Installing web UI dependencies..."
    Push-Location $uiDir
    npm install
    Pop-Location
}

Write-Output "Starting Python backend..."
Start-Process -NoNewWindow powershell -ArgumentList "-NoProfile", "-Command", "cd '$pyDir'; & '$backendExe' --config policy.toml"

Write-Output "Starting Next.js UI (dev server)..."
Start-Process -NoNewWindow powershell -ArgumentList "-NoProfile", "-Command", "cd '$uiDir'; npm run dev"

if ($WithHooks) {
    Write-Output "Starting OS hook streamer..."
    Start-Process -NoNewWindow powershell -ArgumentList "-NoProfile", "-Command", "cd '$pyDir'; & '$hookExe' --endpoint http://127.0.0.1:8000/events"
}

Write-Output "Launched. UI available at http://localhost:3000 (Next dev)."
