# Windows PowerShell script to execute all AttendPlan quality gates
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Running AttendPlan Quality Gates (F2-B) " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$backendDir = Join-Path $PSScriptRoot "backend"
$frontendDir = Join-Path $PSScriptRoot "frontend"
$pytestExe = Join-Path $backendDir ".venv\Scripts\pytest.exe"
$mypyExe = Join-Path $backendDir ".venv\Scripts\mypy.exe"
$ruffExe = Join-Path $backendDir ".venv\Scripts\ruff.exe"

# Gate 1: Backend Domain & Unit Tests
Write-Host "`n[Gate 1/5] Executing Backend Pytest Suites..." -ForegroundColor Yellow
Set-Location $backendDir
& $pytestExe tests -v
if ($LASTEXITCODE -ne 0) { throw "Backend pytest failed!" }

# Gate 2: Backend Typing & Linting
Write-Host "`n[Gate 2/5] Executing Mypy Static Type Checking..." -ForegroundColor Yellow
& $mypyExe app tests
if ($LASTEXITCODE -ne 0) { throw "Mypy type check failed!" }

Write-Host "`n[Gate 3/5] Executing Ruff Linter..." -ForegroundColor Yellow
& $ruffExe check app tests
if ($LASTEXITCODE -ne 0) { throw "Ruff linter failed!" }

# Gate 4: Frontend Tests & Typecheck
Write-Host "`n[Gate 4/5] Executing Frontend Vitest & TypeScript Check..." -ForegroundColor Yellow
Set-Location $frontendDir
& npm.cmd run typecheck
if ($LASTEXITCODE -ne 0) { throw "Frontend TypeScript typecheck failed!" }

& npm.cmd run test
if ($LASTEXITCODE -ne 0) { throw "Frontend Vitest tests failed!" }

# Gate 5: Frontend Production Bundle
Write-Host "`n[Gate 5/5] Building Frontend Production Bundle..." -ForegroundColor Yellow
& npm.cmd run build
if ($LASTEXITCODE -ne 0) { throw "Frontend production build failed!" }

Write-Host "`n==================================================" -ForegroundColor Green
Write-Host " ALL ATTENDPLAN QUALITY GATES PASSED SUCCESSFULLY! " -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green
