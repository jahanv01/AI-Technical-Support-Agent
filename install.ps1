# Usage:
#   .\install.ps1 -ApiKey YOUR_GEMINI_KEY
#   .\install.ps1 -ApiKey YOUR_GEMINI_KEY -Port 8080
param(
    [Parameter(Mandatory=$true)]
    [string]$ApiKey,
    [int]$Port = 8000
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── detect python ─────────────────────────────────────────────────────────────
$python = $null
foreach ($cmd in @("python", "python3")) {
    if (Get-Command $cmd -ErrorAction SilentlyContinue) {
        $ver = & $cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
        $major, $minor = $ver.Split(".")
        if ([int]$major -ge 3 -and [int]$minor -ge 9) { $python = $cmd; break }
    }
}
if (-not $python) {
    Write-Error "Python 3.9+ not found. Install from https://python.org and retry."
    exit 1
}
Write-Host "Using $($python): $(& $python --version)"

# ── virtual environment ───────────────────────────────────────────────────────
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..."
    & $python -m venv .venv
}

$pip      = ".venv\Scripts\pip.exe"
$uvicorn  = ".venv\Scripts\uvicorn.exe"
$streamlit = ".venv\Scripts\streamlit.exe"
$pyExe    = ".venv\Scripts\python.exe"

Write-Host "Installing dependencies..."
& $pip install --quiet --upgrade pip
& $pip install --quiet -r requirements.txt

# ── environment file ──────────────────────────────────────────────────────────
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }

$envContent = Get-Content ".env" -Raw
if ($envContent -match "(?m)^GEMINI_API_KEY=.*$") {
    $envContent = $envContent -replace "(?m)^GEMINI_API_KEY=.*$", "GEMINI_API_KEY=$ApiKey"
} else {
    $envContent += "`nGEMINI_API_KEY=$ApiKey"
}
Set-Content ".env" $envContent -NoNewline

# ── start API server ──────────────────────────────────────────────────────────
if (Test-Path ".server.pid") {
    $oldPid = Get-Content ".server.pid"
    $oldProc = Get-Process -Id $oldPid -ErrorAction SilentlyContinue
    if ($oldProc) {
        Write-Host "Stopping previous server (PID $oldPid)..."
        Stop-Process -Id $oldPid -Force
        Start-Sleep -Seconds 1
    }
    Remove-Item ".server.pid"
}

Write-Host "Starting API server on port $Port..."
$serverProc = Start-Process -FilePath $uvicorn `
    -ArgumentList "app.api:app", "--host", "127.0.0.1", "--port", "$Port" `
    -RedirectStandardOutput "server.log" -RedirectStandardError "server_err.log" `
    -PassThru -WindowStyle Hidden
$serverProc.Id | Set-Content ".server.pid"

# wait up to 10 s for server to be ready
$ready = $false
for ($i = 0; $i -lt 20; $i++) {
    try {
        $null = Invoke-WebRequest "http://127.0.0.1:$Port/docs" -UseBasicParsing -TimeoutSec 1
        $ready = $true; break
    } catch { Start-Sleep -Milliseconds 500 }
}

Write-Host ""
Write-Host "OK Server running (PID $($serverProc.Id))"
Write-Host "   Swagger UI : http://127.0.0.1:$Port/docs"
Write-Host ""

# ── live sample calls ─────────────────────────────────────────────────────────
Write-Host "--- Task 1 - Triage sample ---"
$body = '{"subject":"SSO configuration not working for new users","body":"308 people blocked from accessing the platform since this morning."}'
try {
    $r = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/triage" -Method Post `
        -ContentType "application/json" -Body $body
    $r | ConvertTo-Json -Depth 10
} catch { Write-Warning "Triage call failed: $_" }
Write-Host ""

Write-Host "--- Task 2 - Account brief (ACC-2944) ---"
try {
    $r2 = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/account-brief/ACC-2944"
    $r2 | ConvertTo-Json -Depth 10
} catch { Write-Warning "Account brief call failed: $_" }
Write-Host ""

# ── start Streamlit ───────────────────────────────────────────────────────────
$streamlitPort = 8501
if (Test-Path ".streamlit.pid") {
    $oldSpid = Get-Content ".streamlit.pid"
    $oldSproc = Get-Process -Id $oldSpid -ErrorAction SilentlyContinue
    if ($oldSproc) { Stop-Process -Id $oldSpid -Force; Start-Sleep -Seconds 1 }
    Remove-Item ".streamlit.pid"
}

$slProc = Start-Process -FilePath $streamlit `
    -ArgumentList "run", "ui/streamlit_app.py", "--server.headless", "true", "--server.port", "$streamlitPort" `
    -RedirectStandardOutput "streamlit.log" -RedirectStandardError "streamlit_err.log" `
    -PassThru -WindowStyle Hidden
$slProc.Id | Set-Content ".streamlit.pid"

for ($i = 0; $i -lt 16; $i++) {
    try {
        $null = Invoke-WebRequest "http://localhost:$streamlitPort" -UseBasicParsing -TimeoutSec 1
        break
    } catch { Start-Sleep -Milliseconds 500 }
}

Write-Host "--- Next steps ---"
Write-Host "  Run eval harness:"
Write-Host "    .venv\Scripts\python.exe -m eval.run_eval"
Write-Host ""
Write-Host "  * Bonus UI (TAM demo):"
Write-Host "     http://localhost:$streamlitPort"
Write-Host ""
Write-Host "  To stop everything: .\uninstall.ps1"
