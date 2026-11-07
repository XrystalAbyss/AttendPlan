# AttendPlan Dedicated Chrome Launcher
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$chromeCandidates = @(
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
)

$chromeExe = $null
foreach ($cand in $chromeCandidates) {
    if (Test-Path $cand) {
        $chromeExe = $cand
        break
    }
}

if (-not $chromeExe) {
    Write-Error "Google Chrome executable was not found."
    exit 1
}

$profileDir = Join-Path $env:LOCALAPPDATA "AttendPlan\chrome-profile"
if (-not (Test-Path $profileDir)) {
    New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
}

Write-Host "Launching Dedicated Chrome with Loopback CDP (127.0.0.1:9222)..." -ForegroundColor Cyan

Start-Process -FilePath $chromeExe -ArgumentList @(
    "--remote-debugging-port=9222",
    "--remote-debugging-address=127.0.0.1",
    "--user-data-dir=$profileDir",
    "--no-first-run",
    "--no-default-browser-check",
    "https://mrei.icloudems.com/corecampus/index.php"
)

Write-Host "Chrome launched successfully on your screen!" -ForegroundColor Green
