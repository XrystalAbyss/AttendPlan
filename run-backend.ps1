# Windows PowerShell script to start AttendPlan backend server
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "Starting AttendPlan Backend on http://127.0.0.1:8000..." -ForegroundColor Cyan

$backendDir = Join-Path $PSScriptRoot "backend"
$pythonExe = Join-Path $backendDir ".venv\Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    Write-Host "Virtual environment not found at $pythonExe. Please run setup first." -ForegroundColor Red
    exit 1
}

Set-Location $backendDir
& $pythonExe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
