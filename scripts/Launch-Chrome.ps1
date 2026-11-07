# AttendPlan - Dedicated Chrome Launcher with CDP
# Launches ONLY the dedicated AttendPlan Chrome profile on loopback CDP (127.0.0.1:9222)
# Preserves existing session data, cookies, and tokens. Never resets profile.

[CmdletBinding()]
param(
    [switch]$Quiet = $false
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Log-Ok([string]$msg) {
    Write-Host "      [OK] $msg" -ForegroundColor Green
}

function Log-Error([string]$msg) {
    Write-Host "      [ERROR] $msg" -ForegroundColor Red
}

function Log-Info([string]$msg) {
    Write-Host "      [INFO] $msg" -ForegroundColor Cyan
}

# 1. Resolve repository root
$repoRoot = Split-Path -Parent $PSScriptRoot

# 2. Locate Google Chrome executable
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
    Write-Host "             Please install Google Chrome from https://www.google.com/chrome/" -ForegroundColor Yellow
    exit 1
}

# 3. Locate and verify dedicated Chrome user profile
$profileDir = Join-Path $env:LOCALAPPDATA "AttendPlan\chrome-profile"
if (-not (Test-Path -LiteralPath $profileDir)) {
    New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
}

$portalUrl = "https://mrei.icloudems.com/corecampus/index.php"

# 4. Check existing CDP endpoint and verify process ownership
$cdpVersionUrl = "http://127.0.0.1:9222/json/version"
$cdpListUrl = "http://127.0.0.1:9222/json/list"
$isAlreadyRunning = $false

try {
    $resp = Invoke-RestMethod -Uri $cdpVersionUrl -TimeoutSec 2 -ErrorAction Stop
    if ($resp -and ($resp.Browser -or $resp."Protocol-Version")) {
        # Port 9222 is responding. Verify process ownership.
        $conn = Get-NetTCPConnection -LocalAddress "127.0.0.1" -LocalPort 9222 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($conn) {
            $owningPid = $conn.OwningProcess
            $proc = Get-CimInstance Win32_Process -Filter "ProcessId = $owningPid" -ErrorAction SilentlyContinue
            if ($proc) {
                if ($proc.Name -notmatch "chrome") {
                    Log-Error "Port 9222 is occupied by an unrelated non-Chrome process: $($proc.Name) (PID: $owningPid)."
                    Write-Host "             Cannot attach dedicated AttendPlan browser. Please free port 9222." -ForegroundColor Yellow
                    exit 1
                }
                # If command line is visible, verify profile
                if ($proc.CommandLine -and ($proc.CommandLine -notmatch [regex]::Escape("AttendPlan\chrome-profile")) -and ($proc.CommandLine -notmatch [regex]::Escape($profileDir))) {
                    Log-Error "Port 9222 is occupied by an external Chrome instance not using AttendPlan's dedicated profile."
                    Write-Host "             Process PID: $owningPid" -ForegroundColor Yellow
                    Write-Host "             Command line: $($proc.CommandLine)" -ForegroundColor DarkGray
                    Write-Host "             Please close external debug instances on 9222 before launching AttendPlan." -ForegroundColor Yellow
                    exit 1
                }
            }
        }
        $isAlreadyRunning = $true
    }
} catch {
    $isAlreadyRunning = $false
}

if ($isAlreadyRunning) {
    if (-not $Quiet) {
        Log-Ok "Chrome found: $chromeExe"
        Log-Ok "AttendPlan profile located: $profileDir"
        Log-Ok "Dedicated browser already running (reused existing process)"
        Log-Ok "CDP connection verified on 127.0.0.1:9222"
    }

    # Ensure portal tab is open
    try {
        $tabs = Invoke-RestMethod -Uri $cdpListUrl -TimeoutSec 2 -ErrorAction SilentlyContinue
        $hasPortalTab = $false
        if ($tabs) {
            foreach ($t in $tabs) {
                if ($t.url -and ($t.url -match "icloudems" -or $t.url -match "mrei")) {
                    $hasPortalTab = $true
                    break
                }
            }
        }
        if (-not $hasPortalTab) {
            try {
                Invoke-RestMethod -Uri "http://127.0.0.1:9222/json/new?$portalUrl" -Method Put -TimeoutSec 2 -ErrorAction Stop | Out-Null
            } catch {
                try {
                    Invoke-RestMethod -Uri "http://127.0.0.1:9222/json/new?$portalUrl" -Method Get -TimeoutSec 2 -ErrorAction SilentlyContinue | Out-Null
                } catch {}
            }
        }
    } catch {
        # Non-critical tab navigation
    }

    if (-not $Quiet) {
        Log-Ok "University portal ready: $portalUrl"
    }
    exit 0
}

# 5. Launch dedicated Chrome instance
$chromeArgs = @(
    "--remote-debugging-port=9222",
    "--remote-debugging-address=127.0.0.1",
    "--user-data-dir=$profileDir",
    "--no-first-run",
    "--no-default-browser-check",
    $portalUrl
)

try {
    Start-Process -FilePath $chromeExe -ArgumentList $chromeArgs
} catch {
    Log-Error "Failed to start Google Chrome process: $_"
    exit 1
}

# 6. Wait for CDP endpoint readiness
$maxRetries = 20
$ready = $false
for ($i = 0; $i -lt $maxRetries; $i++) {
    Start-Sleep -Milliseconds 500
    try {
        $resp = Invoke-RestMethod -Uri $cdpVersionUrl -TimeoutSec 1 -ErrorAction Stop
        if ($resp -and ($resp.Browser -or $resp."Protocol-Version")) {
            $ready = $true
            break
        }
    } catch {
        # Retry until timeout
    }
}

if (-not $ready) {
    Log-Error "Dedicated Chrome started, but CDP endpoint 127.0.0.1:9222 failed to respond within 10 seconds."
    exit 1
}

if (-not $Quiet) {
    Log-Ok "Chrome found: $chromeExe"
    Log-Ok "AttendPlan profile located: $profileDir"
    Log-Ok "Dedicated browser started successfully"
    Log-Ok "CDP connection verified on 127.0.0.1:9222"
    Log-Ok "University portal ready: $portalUrl"
}

exit 0
