# AttendPlan - Process Shutdown Helper
# Cleanly terminates owned backend and frontend processes using stored PIDs.
# Preserves dedicated Chrome and existing session data.

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "       STOPPING ATTENDPLAN SERVICES       " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$runDir = Join-Path $env:LOCALAPPDATA "AttendPlan\run"
$backendPidFile = Join-Path $runDir "backend.pid"
$frontendPidFile = Join-Path $runDir "frontend.pid"

# 1. Stop backend process
$stoppedBackend = $false
if (Test-Path $backendPidFile) {
    try {
        $bPid = [int](Get-Content $backendPidFile -Raw).Trim()
        $proc = Get-Process -Id $bPid -ErrorAction SilentlyContinue
        if ($proc -and ($proc.ProcessName -match "python")) {
            Stop-Process -Id $bPid -Force -ErrorAction SilentlyContinue
            $stoppedBackend = $true
        }
    } catch {}
    Remove-Item $backendPidFile -Force -ErrorAction SilentlyContinue
}

# Fallback: check if verified AttendPlan backend on port 8000 is running
try {
    $conn = Get-NetTCPConnection -LocalPort 8000 -LocalAddress "127.0.0.1" -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($conn) {
        $isAttendPlan = $false
        try {
            $h = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 1 -ErrorAction Stop
            if ($h -and $h.app -eq "AttendPlan") {
                $isAttendPlan = $true
            }
        } catch {}

        if ($isAttendPlan) {
            $p = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
            if ($p -and $p.ProcessName -match "python") {
                Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
                $stoppedBackend = $true
            }
        } else {
            Write-Host "  [WARN] Port 8000 is occupied by a non-AttendPlan process (PID: $($conn.OwningProcess)). Preserving it." -ForegroundColor Yellow
        }
    }
} catch {}

if ($stoppedBackend) {
    Write-Host "  [OK] AttendPlan FastAPI backend stopped." -ForegroundColor Green
} else {
    Write-Host "  [INFO] AttendPlan backend was not running." -ForegroundColor Gray
}

# 2. Stop frontend process
$stoppedFrontend = $false
if (Test-Path $frontendPidFile) {
    try {
        $fPid = [int](Get-Content $frontendPidFile -Raw).Trim()
        $proc = Get-Process -Id $fPid -ErrorAction SilentlyContinue
        if ($proc) {
            # Kill process tree (npm spawns node)
            Stop-Process -Id $fPid -Force -ErrorAction SilentlyContinue
            $stoppedFrontend = $true
        }
    } catch {}
    Remove-Item $frontendPidFile -Force -ErrorAction SilentlyContinue
}

# Fallback: check if node/vite is listening on port 5173 and belongs to AttendPlan
try {
    $conn5173 = Get-NetTCPConnection -LocalPort 5173 -LocalAddress "127.0.0.1" -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($conn5173) {
        $isViteFrontend = $false
        try {
            $cim = Get-CimInstance Win32_Process -Filter "ProcessId = $($conn5173.OwningProcess)" -ErrorAction SilentlyContinue
            if ($cim -and ($cim.CommandLine -match "vite" -or $cim.CommandLine -match "AttendPlan")) {
                $isViteFrontend = $true
            }
        } catch {}

        if ($isViteFrontend) {
            Stop-Process -Id $conn5173.OwningProcess -Force -ErrorAction SilentlyContinue
            $stoppedFrontend = $true
        }
    }
} catch {}

if ($stoppedFrontend) {
    Write-Host "  [OK] AttendPlan Vite frontend stopped." -ForegroundColor Green
} else {
    Write-Host "  [INFO] AttendPlan frontend was not running." -ForegroundColor Gray
}

# 3. Dedicated Chrome preservation notice
Write-Host "  [INFO] Dedicated Chrome browser was preserved." -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "AttendPlan background services stopped." -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
