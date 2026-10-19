# Windows PowerShell script to start AttendPlan frontend Vite dev server
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "Starting AttendPlan Frontend on http://localhost:5173..." -ForegroundColor Cyan

$frontendDir = Join-Path $PSScriptRoot "frontend"
Set-Location $frontendDir

& npm.cmd run dev
