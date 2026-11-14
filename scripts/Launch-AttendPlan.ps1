# AttendPlan - Full Application Launcher
# Starts Dedicated Chrome, FastAPI Backend, React/Vite Frontend, and opens Dashboard.
# Completely local-first, zero cloud dependencies, single-instance safe.

[CmdletBinding()]
param(
    [switch]$Stop = $false,
    [switch]$ForceSwitch = $false
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($Stop) {
    & "$PSScriptRoot\Stop-AttendPlan.ps1"
    exit 0
}

function Log-Step([string]$num, [string]$title) {
    Write-Host "`n[$num] $title" -ForegroundColor Yellow
}

function Log-Ok([string]$msg) {
    Write-Host "      [OK] $msg" -ForegroundColor Green
}

function Log-Error([string]$msg) {
    Write-Host "      [ERROR] $msg" -ForegroundColor Red
}

function Log-Info([string]$msg) {
    Write-Host "      [INFO] $msg" -ForegroundColor Cyan
}

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "               ATTENDPLAN                 " -ForegroundColor Cyan
Write-Host "        Local Attendance Planner          " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$repoRoot = Split-Path -Parent $PSScriptRoot
$runDir = Join-Path $env:LOCALAPPDATA "AttendPlan\run"
if (-not (Test-Path -LiteralPath $runDir)) {
    New-Item -ItemType Directory -Path $runDir -Force | Out-Null
}

$backendPidFile = Join-Path $runDir "backend.pid"
$frontendPidFile = Join-Path $runDir "frontend.pid"

# -------------------------------------------------------------
# [1/5] Checking environment...
# -------------------------------------------------------------
Log-Step "1/5" "Checking environment..."

$pythonExe = Join-Path $repoRoot "backend\.venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $pythonExe)) {
    Log-Error "Python virtual environment not found at backend\.venv"
    Write-Host "             Please run environment setup first:" -ForegroundColor Yellow
    Write-Host "               cd backend" -ForegroundColor Gray
    Write-Host "               python -m venv .venv" -ForegroundColor Gray
    Write-Host "               .venv\Scripts\pip install -r requirements.txt" -ForegroundColor Gray
    exit 1
}
Log-Ok "Python environment ready: backend\.venv"

$nodeModules = Join-Path $repoRoot "frontend\node_modules"
if (-not (Test-Path -LiteralPath $nodeModules)) {
    Log-Error "Frontend Node.js dependencies not found at frontend\node_modules"
    Write-Host "             Please run setup first:" -ForegroundColor Yellow
    Write-Host "               cd frontend" -ForegroundColor Gray
    Write-Host "               npm install" -ForegroundColor Gray
    exit 1
}
Log-Ok "Node.js dependencies ready: frontend\node_modules"

$chromeCandidates = @(
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
)
$chromeExe = $null
foreach ($cand in $chromeCandidates) {
    if (Test-Path -LiteralPath $cand) {
        $chromeExe = $cand
        break
    }
}
if (-not $chromeExe) {
    Log-Error "Google Chrome executable was not found on this system."
    exit 1
}
Log-Ok "Google Chrome located"

# -------------------------------------------------------------
# [2/5] Starting dedicated Chrome...
# -------------------------------------------------------------
Log-Step "2/5" "Starting dedicated Chrome..."

& "$PSScriptRoot\Launch-Chrome.ps1" -Quiet
if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) {
    Log-Error "Failed to start or verify dedicated Chrome."
    exit 1
}
Log-Ok "CDP 127.0.0.1:9222 verified"
Log-Ok "University portal ready"

# -------------------------------------------------------------
# [3/5] Starting backend...
# -------------------------------------------------------------
Log-Step "3/5" "Starting backend..."

# Set development environment for dev launcher
$env:ATTENDPLAN_ENV = "development"

$backendUrl = "http://127.0.0.1:8000"
$healthUrl = "$backendUrl/health"
$backendAlreadyRunning = $false

try {
    $healthResp = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 2 -ErrorAction Stop
    if ($healthResp -and $healthResp.app -eq "AttendPlan" -and $healthResp.status -eq "healthy") {
        $existingRuntime = if ($healthResp.runtime) { $healthResp.runtime } else { "unknown" }
        $existingMode = if ($healthResp.mode) { $healthResp.mode } else { "production" }

        # Identify process listening on port 8000
        $portConn = Get-NetTCPConnection -LocalPort 8000 -LocalAddress "127.0.0.1" -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
        $owningPid = if ($portConn) { $portConn.OwningProcess } else { $null }
        $procInfo = if ($owningPid) { Get-Process -Id $owningPid -ErrorAction SilentlyContinue } else { $null }
        $procPath = if ($procInfo -and $procInfo.Path) { $procInfo.Path } else { "Unknown" }
        $procName = if ($procInfo) { $procInfo.ProcessName } else { "Unknown" }

        if ($existingRuntime -eq "source" -and $existingMode -eq "development") {
            $backendAlreadyRunning = $true
            Log-Ok "$backendUrl (reused existing source development instance, PID: $owningPid)"
        } else {
            # Query detailed diagnostic status
            $statusResp = $null
            try {
                $statusResp = Invoke-RestMethod -Uri "$backendUrl/api/v1/startup/status" -TimeoutSec 2 -ErrorAction Stop
            } catch {
                # Status endpoint might not be accessible or timed out
            }

            $instanceToken = if ($statusResp -and $statusResp.instance_token) { $statusResp.instance_token } else { $null }
            $existingDb = if ($statusResp -and $statusResp.database_path) { $statusResp.database_path } else { "Default (%LOCALAPPDATA%\AttendPlan\attendplan.sqlite3)" }
            $isSyncing = if ($statusResp -and ($statusResp.active_sync -or $statusResp.running -or $statusResp.state -in @("SYNCING", "DISCOVERING", "LOGGING_IN"))) { $true } else { $false }

            # Safety check: Never terminate an active synchronization job or database write
            if ($isSyncing) {
                Log-Error "The running AttendPlan instance (PID: $owningPid) is currently executing an active synchronization job."
                Write-Host "             Never interrupt active portal synchronization or database writes." -ForegroundColor Red
                Write-Host "             Please wait for the current synchronization to complete before switching runtimes." -ForegroundColor Yellow
                exit 1
            }

            # Clear conflict explanation
            Write-Host "`n[RUNTIME CONFLICT] Port 8000 is occupied by a running AttendPlan instance:" -ForegroundColor Yellow
            Write-Host "  - Process Name    : $procName (PID: $owningPid)" -ForegroundColor Gray
            Write-Host "  - Executable Path : $procPath" -ForegroundColor Gray
            Write-Host "  - Runtime & Mode  : $existingRuntime runtime ($existingMode mode)" -ForegroundColor Gray
            Write-Host "  - Database Target : $existingDb" -ForegroundColor Gray
            Write-Host "  - Active Sync Job : None (Idle, safe to switch)" -ForegroundColor Gray
            Write-Host "  - Required Mode   : Source backend in development mode (ATTENDPLAN_ENV=development)`n" -ForegroundColor Cyan

            # Explicit approval required to switch runtimes
            $approved = $false
            if ($ForceSwitch) {
                Log-Info "-ForceSwitch parameter supplied. Proceeding with graceful runtime switch."
                $approved = $true
            } elseif ([Environment]::UserInteractive) {
                $promptAnswer = Read-Host "Do you want to gracefully stop the running instance (PID: $owningPid) to switch to development mode? [y/N]"
                if ($promptAnswer -match "^[yY]$") {
                    $approved = $true
                }
            } else {
                Log-Error "Running instance detected on port 8000 in non-interactive session without -ForceSwitch."
                Write-Host "             Run with -ForceSwitch to approve stopping the running instance." -ForegroundColor Yellow
                exit 1
            }

            if (-not $approved) {
                Log-Info "Switch cancelled by user. The running instance (PID: $owningPid) was not modified or terminated."
                exit 0
            }

            Write-Host "             Requesting graceful shutdown of the existing instance..." -ForegroundColor Cyan
            $shutdownSuccess = $false
            try {
                $headers = @{}
                if ($instanceToken) {
                    $headers["X-AttendPlan-Instance"] = $instanceToken
                }
                $null = Invoke-RestMethod -Uri "$backendUrl/api/v1/startup/shutdown" -Method Post -Headers $headers -TimeoutSec 3 -ErrorAction Stop
                
                # Wait up to 10 seconds for process exit and port release
                for ($k = 0; $k -lt 20; $k++) {
                    Start-Sleep -Milliseconds 500
                    $stillListening = Get-NetTCPConnection -LocalPort 8000 -LocalAddress "127.0.0.1" -State Listen -ErrorAction SilentlyContinue
                    $stillProc = if ($owningPid) { Get-Process -Id $owningPid -ErrorAction SilentlyContinue } else { $null }
                    if (-not $stillListening -and -not $stillProc) {
                        $shutdownSuccess = $true
                        break
                    }
                }
            } catch {
                Log-Info "Graceful shutdown via API encountered: $_"
            }

            if ($shutdownSuccess) {
                Log-Ok "Gracefully stopped existing instance (PID: $owningPid). Port 8000 released."
                $backendAlreadyRunning = $false
            } else {
                Log-Error "Could not safely verify exit of instance (PID: $owningPid). Port 8000 not released."
                Write-Host "             Please close the running AttendPlan application before launching development mode." -ForegroundColor Yellow
                exit 1
            }
        }
    }
} catch {
    $backendAlreadyRunning = $false
}

if (-not $backendAlreadyRunning) {
    # Check if port 8000 is occupied by an unrelated foreign process
    $occupied8000 = Get-NetTCPConnection -LocalPort 8000 -LocalAddress "127.0.0.1" -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($occupied8000) {
        Log-Error "Port 8000 is occupied by an unrelated process (PID: $($occupied8000.OwningProcess))."
        Write-Host "             Cannot start AttendPlan backend. Please free port 8000." -ForegroundColor Yellow
        exit 1
    }

    $backendDir = Join-Path $repoRoot "backend"
    try {
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = $pythonExe
        $psi.Arguments = "-m uvicorn app.main:app --host 127.0.0.1 --port 8000"
        $psi.WorkingDirectory = $backendDir
        $psi.EnvironmentVariables["ATTENDPLAN_ENV"] = "development"
        $psi.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
        $psi.UseShellExecute = $false
        $bProc = [System.Diagnostics.Process]::Start($psi)
        Set-Content -Path $backendPidFile -Value $bProc.Id -Force
    } catch {
        Log-Error "Failed to spawn backend process: $_"
        exit 1
    }

    # Wait for backend healthcheck
    $backendReady = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Milliseconds 500
        try {
            $resp = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 1 -ErrorAction Stop
            if ($resp -and $resp.app -eq "AttendPlan" -and $resp.status -eq "healthy") {
                $backendReady = $true
                break
            }
        } catch {}
    }

    if (-not $backendReady) {
        Log-Error "Backend failed to report healthy at $healthUrl within 15 seconds."
        if ($bProc -and -not $bProc.HasExited) {
            Stop-Process -Id $bProc.Id -Force -ErrorAction SilentlyContinue
        }
        Remove-Item $backendPidFile -Force -ErrorAction SilentlyContinue
        exit 1
    }

    Log-Ok "$backendUrl (started PID: $($bProc.Id))"
}

# -------------------------------------------------------------
# [4/5] Starting frontend...
# -------------------------------------------------------------
Log-Step "4/5" "Starting frontend..."

$frontendUrl = "http://127.0.0.1:5173"
$frontendAlreadyRunning = $false

try {
    $feResp = Invoke-WebRequest -Uri $frontendUrl -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
    if ($feResp.StatusCode -eq 200) {
        $frontendAlreadyRunning = $true
        Log-Ok "$frontendUrl (reused existing healthy instance)"
    }
} catch {
    $frontendAlreadyRunning = $false
}

if (-not $frontendAlreadyRunning) {
    # Check if port 5173 is occupied by unrelated process
    $occupied5173 = Get-NetTCPConnection -LocalPort 5173 -LocalAddress "127.0.0.1" -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($occupied5173) {
        Log-Error "Port 5173 is occupied by an unrelated process (PID: $($occupied5173.OwningProcess))."
        Write-Host "             Cannot start Vite frontend. Please free port 5173." -ForegroundColor Yellow
        exit 1
    }

    $frontendDir = Join-Path $repoRoot "frontend"
    try {
        $fProc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "npm.cmd", "run", "dev", "--", "--strictPort", "--host", "127.0.0.1", "--port", "5173" -WorkingDirectory $frontendDir -PassThru -WindowStyle Hidden
        Set-Content -Path $frontendPidFile -Value $fProc.Id -Force
    } catch {
        Log-Error "Failed to spawn frontend process: $_"
        exit 1
    }

    # Wait for frontend readiness
    $frontendReady = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Milliseconds 500
        try {
            $resp = Invoke-WebRequest -Uri $frontendUrl -TimeoutSec 1 -UseBasicParsing -ErrorAction Stop
            if ($resp.StatusCode -eq 200) {
                $frontendReady = $true
                break
            }
        } catch {}
    }

    if (-not $frontendReady) {
        Log-Error "Frontend failed to respond at $frontendUrl within 15 seconds."
        if ($fProc -and -not $fProc.HasExited) {
            Stop-Process -Id $fProc.Id -Force -ErrorAction SilentlyContinue
        }
        Remove-Item $frontendPidFile -Force -ErrorAction SilentlyContinue
        exit 1
    }

    Log-Ok "$frontendUrl (started PID: $($fProc.Id))"
}

# -------------------------------------------------------------
# [5/5] Opening dashboard...
# -------------------------------------------------------------
Log-Step "5/5" "Opening dashboard..."

try {
    $tabs = Invoke-RestMethod -Uri "http://127.0.0.1:9222/json/list" -TimeoutSec 2 -ErrorAction SilentlyContinue
    $hasDashboardTab = $false
    if ($tabs) {
        foreach ($t in $tabs) {
            if ($t.url -and ($t.url -match "5173")) {
                $hasDashboardTab = $true
                break
            }
        }
    }

    if (-not $hasDashboardTab) {
        $opened = $false
        try {
            Invoke-RestMethod -Uri "http://127.0.0.1:9222/json/new?$frontendUrl" -Method Put -TimeoutSec 2 -ErrorAction Stop | Out-Null
            $opened = $true
        } catch {
            try {
                Invoke-RestMethod -Uri "http://127.0.0.1:9222/json/new?$frontendUrl" -Method Get -TimeoutSec 2 -ErrorAction SilentlyContinue | Out-Null
                $opened = $true
            } catch {}
        }
        if ($opened) {
            Log-Ok "Opened AttendPlan dashboard in dedicated Chrome tab"
        }
    } else {
        Log-Ok "AttendPlan dashboard is already open in Chrome"
    }
} catch {
    Log-Info "Dedicated Chrome is running; browse to $frontendUrl"
}

Log-Ok "AttendPlan ready"

Write-Host "`n==========================================" -ForegroundColor Green
Write-Host "     SUCCESS -- ATTENDPLAN IS RUNNING      " -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host "  Dashboard:   $frontendUrl" -ForegroundColor Cyan
Write-Host "  API Health:  $healthUrl" -ForegroundColor Cyan
Write-Host "  Portal CDP:  127.0.0.1:9222" -ForegroundColor Cyan
Write-Host ""
Write-Host "  To stop background services:" -ForegroundColor Yellow
Write-Host "  Run scripts\Stop-AttendPlan.cmd (or Launch-AttendPlan.cmd -Stop)" -ForegroundColor Gray
Write-Host "==========================================" -ForegroundColor Green
exit 0
