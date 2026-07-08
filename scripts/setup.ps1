# ==============================================================================
# LOGISECURE AI - ONE-COMMAND DEV SETUP (Windows / PowerShell)
# Usage (from anywhere):   .\scripts\setup.ps1
# Creates backend/.venv, installs dependencies, prepares backend/.env
# ==============================================================================
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Backend  = Join-Path $RepoRoot "backend"

Write-Host "`n=== LogiSecure AI :: Backend Dev Setup ===" -ForegroundColor Cyan

# 1. Verify Python
try { $pyVersion = (python --version) 2>&1 } catch { $pyVersion = $null }
if (-not $pyVersion) {
    Write-Host "Python not found. Install Python 3.10+ from https://python.org and retry." -ForegroundColor Red
    exit 1
}
Write-Host "[1/4] Using $pyVersion"

# 2. Virtual environment
$Venv = Join-Path $Backend ".venv"
if (-not (Test-Path $Venv)) {
    Write-Host "[2/4] Creating virtual environment at backend\.venv ..."
    python -m venv $Venv
} else {
    Write-Host "[2/4] Reusing existing backend\.venv"
}

# 3. Dependencies
Write-Host "[3/4] Installing backend dependencies ..."
& (Join-Path $Venv "Scripts\python.exe") -m pip install --upgrade pip --quiet
& (Join-Path $Venv "Scripts\python.exe") -m pip install -r (Join-Path $Backend "requirements.txt")

# 4. Environment file
$EnvFile = Join-Path $Backend ".env"
if (-not (Test-Path $EnvFile)) {
    Copy-Item (Join-Path $RepoRoot ".env.example") $EnvFile
    Write-Host "[4/4] Created backend\.env from .env.example (fill in your API keys)"
} else {
    Write-Host "[4/4] backend\.env already exists - left untouched"
}

Write-Host "`nSetup complete! Run the API with:" -ForegroundColor Green
Write-Host "    cd backend"
Write-Host "    .\.venv\Scripts\Activate.ps1"
Write-Host "    uvicorn main:app --reload"
Write-Host "`nOr skip all of the above and use Docker:" -ForegroundColor Green
Write-Host "    docker compose -f deploy/docker-compose.yml up --build"
Write-Host "`nAPI:    http://localhost:8000"
Write-Host "Docs:   http://localhost:8000/docs"
Write-Host "Health: http://localhost:8000/health`n"
