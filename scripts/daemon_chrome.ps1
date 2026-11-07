# Keep Chrome running in background daemon task
$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
& "$PSScriptRoot\Launch-Chrome.ps1"
Write-Host "Chrome daemon loop started. Monitoring Chrome process..."
while ($true) {
    Start-Sleep -Seconds 30
    $p = Get-Process chrome -ErrorAction SilentlyContinue
    if (-not $p) {
        Write-Host "Chrome process closed, exiting daemon loop."
        break
    }
}

