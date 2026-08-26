# Usage:
#   .\uninstall.ps1
#   .\uninstall.ps1 -KeepEnv   (stop processes only, keep .venv and .env)
param([switch]$KeepEnv)

Set-StrictMode -Version Latest
$ErrorActionPreference = "SilentlyContinue"

# ── stop API server ───────────────────────────────────────────────────────────
if (Test-Path ".server.pid") {
    $pid = Get-Content ".server.pid"
    $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
    if ($proc) {
        Write-Host "Stopping API server (PID $pid)..."
        Stop-Process -Id $pid -Force
        Start-Sleep -Seconds 1
        Write-Host "Server stopped."
    } else {
        Write-Host "API server process $pid was not running."
    }
    Remove-Item ".server.pid"
} else {
    Write-Host "No .server.pid found."
}

# ── stop Streamlit ────────────────────────────────────────────────────────────
if (Test-Path ".streamlit.pid") {
    $spid = Get-Content ".streamlit.pid"
    $sproc = Get-Process -Id $spid -ErrorAction SilentlyContinue
    if ($sproc) {
        Write-Host "Stopping Streamlit UI (PID $spid)..."
        Stop-Process -Id $spid -Force
        Start-Sleep -Seconds 1
        Write-Host "Streamlit stopped."
    } else {
        Write-Host "Streamlit process $spid was not running."
    }
    Remove-Item ".streamlit.pid"
}

Remove-Item "server.log", "server_err.log", "streamlit.log", "streamlit_err.log" -ErrorAction SilentlyContinue

# ── clean up ──────────────────────────────────────────────────────────────────
if (Test-Path ".cache") { Remove-Item ".cache" -Recurse -Force }

if (-not $KeepEnv) {
    if (Test-Path ".venv") { Remove-Item ".venv" -Recurse -Force }
    Write-Host "Removed .venv"
    Write-Host ""
    Write-Host "Note: .env was kept (contains your API key). Remove it manually if needed:"
    Write-Host "  Remove-Item .env"
} else {
    Write-Host "Kept .venv and .env (-KeepEnv)"
}

Write-Host "Done."
