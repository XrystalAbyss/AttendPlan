<#
.SYNOPSIS
AttendPlan Storage & Maintenance Utility
Advanced local-first maintenance tool for diagnosing database integrity,
creating verified SQLite backups, cleaning temporary caches, and executing safe resets.
#>
param(
    [switch]$NonInteractive = $false
)

$ErrorActionPreference = "Stop"

$AppDataLocal = if ($env:LOCALAPPDATA) { $env:LOCALAPPDATA } else { Join-Path $env:USERPROFILE "AppData\Local" }
$AttendPlanDataDir = Join-Path $AppDataLocal "AttendPlan"
$DbPath = Join-Path $AttendPlanDataDir "attendplan.sqlite3"
$SettingsPath = Join-Path $AttendPlanDataDir "settings.json"
$BackupsDir = Join-Path $AttendPlanDataDir "backups"
$EvidenceDir = Join-Path $AttendPlanDataDir "support_evidence"

# Find AttendPlan executable or Python environment
$AppExe = $null
$PossibleExes = @(
    (Join-Path $PSScriptRoot "AttendPlan.exe"),
    (Join-Path $env:APPDATA "AttendPlan\app\AttendPlan.exe"),
    (Join-Path $PSScriptRoot "..\dist\AttendPlan\AttendPlan.exe")
)
foreach ($candidate in $PossibleExes) {
    if (Test-Path $candidate) {
        $AppExe = (Resolve-Path $candidate).Path
        break
    }
}

$PythonExe = $null
$PossiblePythons = @(
    (Join-Path $PSScriptRoot "..\backend\.venv\Scripts\python.exe"),
    (Join-Path $PSScriptRoot "backend\.venv\Scripts\python.exe")
)
foreach ($candidate in $PossiblePythons) {
    if (Test-Path $candidate) {
        $PythonExe = (Resolve-Path $candidate).Path
        break
    }
}

function Show-Header {
    Clear-Host
    Write-Host "==================================================================" -ForegroundColor Cyan
    Write-Host "  AttendPlan — Storage & Maintenance Utility (Advanced)" -ForegroundColor Cyan
    Write-Host "==================================================================" -ForegroundColor Cyan
    Write-Host " Local Data Directory : $AttendPlanDataDir"
    Write-Host " Database Location    : $DbPath"
    if (Test-Path $DbPath) {
        $size = (Get-Item $DbPath).Length
        Write-Host " Database Status      : PRESENT ($([math]::Round($size / 1MB, 2)) MB)" -ForegroundColor Green
    } else {
        Write-Host " Database Status      : NOT FOUND" -ForegroundColor Yellow
    }
    if (Test-Path $SettingsPath) {
        Write-Host " Settings File        : PRESENT" -ForegroundColor Green
    } else {
        Write-Host " Settings File        : NOT FOUND" -ForegroundColor Yellow
    }
    if (Test-Path $EvidenceDir) {
        Write-Host " Security Evidence    : PROTECTED ($((Get-ChildItem $EvidenceDir -Recurse -File).Count) items)" -ForegroundColor Magenta
    }
    Write-Host "==================================================================" -ForegroundColor Cyan
}

function Test-IsAppRunning {
    $conns = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
    if ($conns) {
        return $true
    }
    return $false
}

function Invoke-IntegrityCheck {
    Write-Host "`n[1] Running Storage Health & Database Integrity Check..." -ForegroundColor Yellow
    if (-not (Test-Path $DbPath)) {
        Write-Host "No database found at $DbPath" -ForegroundColor Red
        return
    }

    if ($AppExe) {
        Write-Host "Executing diagnostics via $AppExe --check-db..." -ForegroundColor Gray
        cmd /c "`"$AppExe`" --check-db"
    } elseif ($PythonExe) {
        $launcher = Join-Path $PSScriptRoot "..\backend\launcher.py"
        if (Test-Path $launcher) {
            Write-Host "Executing diagnostics via Python launcher..." -ForegroundColor Gray
            & $PythonExe $launcher --check-db
        }
    } else {
        Write-Host "Database File: $DbPath"
        Write-Host "File Size    : $((Get-Item $DbPath).Length) bytes"
        Write-Host "Last Modified: $((Get-Item $DbPath).LastWriteTime)"
    }

    if (Test-Path $SettingsPath) {
        Write-Host "`nSettings Overview (Non-Sensitive):" -ForegroundColor Gray
        try {
            $raw = Get-Content $SettingsPath -Raw | ConvertFrom-Json
            $mob = $raw.saved_mobile_number
            $masked = if ($mob -and $mob.Length -ge 4) { "******" + $mob.Substring($mob.Length - 4) } else { "None" }
            Write-Host "  Saved Mobile Number    : $masked"
            Write-Host "  Auto Mobile Autofill   : $($raw.auto_mobile_autofill)"
            Write-Host "  Auto Continuation      : $($raw.auto_login_continuation)"
            Write-Host "  Auto TOTP Autofill     : $($raw.auto_totp_autofill)"
        } catch {
            Write-Host "  Failed to parse settings.json: $_" -ForegroundColor Red
        }
    }
}

function Invoke-SafetyBackup {
    param([string]$CustomDest = "")
    Write-Host "`n[2] Creating Verified SQLite Online Safety Backup..." -ForegroundColor Yellow
    if (-not (Test-Path $DbPath)) {
        Write-Host "ERROR: No database file found to back up." -ForegroundColor Red
        return $null
    }

    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupDest = if ($CustomDest) {
        $CustomDest
    } else {
        if (-not (Test-Path $BackupsDir)) {
            New-Item -ItemType Directory -Path $BackupsDir -Force | Out-Null
        }
        Join-Path $BackupsDir "attendplan_backup_$timestamp.sqlite3"
    }

    # Collision check
    if ((Resolve-Path $DbPath -ErrorAction SilentlyContinue).Path -eq (Resolve-Path $backupDest -ErrorAction SilentlyContinue).Path) {
        Write-Host "ERROR: Destination collides with active database. Aborting." -ForegroundColor Red
        return $null
    }

    if ($AppExe) {
        Write-Host "Invoking application online backup engine..." -ForegroundColor Gray
        $output = cmd /c "`"$AppExe`" --backup-db `"$backupDest`""
        $output | Out-Host
        if ($LASTEXITCODE -ne 0) {
            Write-Host "ERROR: Online backup failed with exit code $LASTEXITCODE" -ForegroundColor Red
            return $null
        }
    } elseif ($PythonExe) {
        $launcher = Join-Path $PSScriptRoot "..\backend\launcher.py"
        if (Test-Path $launcher) {
            Write-Host "Invoking Python online backup engine..." -ForegroundColor Gray
            & $PythonExe $launcher --backup-db $backupDest
            if ($LASTEXITCODE -ne 0) {
                Write-Host "ERROR: Python backup engine failed." -ForegroundColor Red
                return $null
            }
        }
    } else {
        Write-Host "ERROR: Neither AttendPlan.exe nor Python launcher is available for online SQLite backup." -ForegroundColor Red
        Write-Host "Raw file copying of an active SQLite database is strictly prohibited to prevent corruption." -ForegroundColor Red
        return $null
    }

    # Verify backup existence and nonzero size
    if (-not (Test-Path $backupDest) -or (Get-Item $backupDest).Length -eq 0) {
        Write-Host "ERROR: Backup verification failed: file does not exist or has zero bytes." -ForegroundColor Red
        return $null
    }

    return $backupDest
}

function Invoke-CacheCleanup {
    Write-Host "`n[3] Cleaning Regenerable Temporary Caches..." -ForegroundColor Yellow
    Write-Host "NOTE: Saved attendance records, courses, settings, and backups will NOT be touched." -ForegroundColor Gray

    if (Test-IsAppRunning) {
        Write-Host "WARNING: AttendPlan is currently running. Please close AttendPlan before cleaning caches." -ForegroundColor Yellow
        $proceed = Read-Host "Proceed anyway? [y/N]"
        if ($proceed -ne "y" -and $proceed -ne "Y") {
            Write-Host "Cache cleanup cancelled." -ForegroundColor Green
            return
        }
    }

    # Note: Correct directory name is 'chrome-profile' (with a hyphen)
    $cacheDirs = @(
        (Join-Path $AttendPlanDataDir "chrome-profile\Default\Cache"),
        (Join-Path $AttendPlanDataDir "chrome-profile\Default\Code Cache"),
        (Join-Path $AttendPlanDataDir "chrome-profile\Default\DawnGraphiteCache"),
        (Join-Path $AttendPlanDataDir "chrome-profile\Default\GPUCache")
    )

    $cleanedCount = 0
    foreach ($dir in $cacheDirs) {
        if (Test-Path $dir) {
            try {
                Remove-Item -Path "$dir\*" -Recurse -Force -ErrorAction SilentlyContinue
                Write-Host "Cleaned Cache: $dir" -ForegroundColor Green
                $cleanedCount++
            } catch {
                Write-Host "Warning: Could not clean $dir (file may be locked)" -ForegroundColor Yellow
            }
        }
    }

    $logsDir = Join-Path $AttendPlanDataDir "logs"
    if (Test-Path $logsDir) {
        try {
            Remove-Item -Path "$logsDir\*.log" -Force -ErrorAction SilentlyContinue
            Write-Host "Cleaned Logs: $logsDir" -ForegroundColor Green
            $cleanedCount++
        } catch {
            Write-Host "Warning: Could not clean logs directory" -ForegroundColor Yellow
        }
    }

    Write-Host "`nCache cleanup finished ($cleanedCount locations processed). Authentication and cookies preserved." -ForegroundColor Green
}

function Invoke-StandardUninstall {
    Write-Host "`n[4] Standard Safe Program Uninstallation..." -ForegroundColor Yellow
    Write-Host "Program binaries and shortcuts will be removed. Your student attendance database, settings, and backups will be safely preserved." -ForegroundColor Gray

    $regKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{C6B5E87D-1F33-4D91-8846-9D923E2A3819}_is1"
    if (Test-Path $regKey) {
        $uninstallerRaw = (Get-ItemProperty -Path $regKey).UninstallString
        if ($uninstallerRaw) {
            # Safely parse executable and arguments
            if ($uninstallerRaw -match '^"([^"]+)"(.*)$') {
                $exePath = $matches[1]
                $argStr = $matches[2].Trim()
            } else {
                $parts = $uninstallerRaw -split ' ', 2
                $exePath = $parts[0]
                $argStr = if ($parts.Length -gt 1) { $parts[1] } else { "" }
            }

            if (Test-Path $exePath) {
                Write-Host "Launching official uninstaller: $exePath" -ForegroundColor Cyan
                $proc = Start-Process -FilePath $exePath -ArgumentList $argStr -Wait -PassThru
                Write-Host "Uninstallation completed with exit code $($proc.ExitCode)." -ForegroundColor Green
                Write-Host "Notice: Your attendance records remain safely preserved in $AttendPlanDataDir." -ForegroundColor Cyan
                return
            }
        }
    }
    Write-Host "No registered Inno Setup uninstaller found in Windows registry." -ForegroundColor Yellow
}

function Invoke-FullReset {
    Write-Host "`n[5] FULL CLEAN RESET / APPLICATION DATA PURGE" -ForegroundColor Red
    Write-Host "==================================================================" -ForegroundColor Red
    Write-Host " WARNING: This will permanently erase your local attendance database," -ForegroundColor Red
    Write-Host " historical records, course catalogs, and saved login preferences." -ForegroundColor Red
    Write-Host " Stored security incident evidence and existing backups will NOT be deleted." -ForegroundColor Yellow
    Write-Host " A verified emergency backup MUST be created before deletion can occur." -ForegroundColor Yellow
    Write-Host "==================================================================" -ForegroundColor Red

    if (Test-IsAppRunning) {
        Write-Host "AttendPlan is currently running. You must close AttendPlan before performing a reset." -ForegroundColor Red
        return
    }

    $confirm = Read-Host "`nType 'DELETE' in capital letters to confirm application data reset"
    if ($confirm -ne "DELETE") {
        Write-Host "`nRESULT: CANCELLED — Reset aborted. No files were modified." -ForegroundColor Green
        return
    }

    $desktopDir = [Environment]::GetFolderPath("Desktop")
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $emergencyBackup = Join-Path $desktopDir "AttendPlan_PreReset_Backup_$timestamp.sqlite3"

    Write-Host "`nInvoking canonical AttendPlan reset engine..." -ForegroundColor Cyan
    $output = @()
    $exitCode = 1

    if ($AppExe) {
        $output = & cmd /c "`"$AppExe`" --reset-app-data --confirm DELETE --backup-dest `"$emergencyBackup`"" 2>&1
        $exitCode = $LASTEXITCODE
    } elseif ($PythonExe) {
        $launcher = Join-Path $PSScriptRoot "..\backend\launcher.py"
        if (-not (Test-Path $launcher)) {
            $launcher = Join-Path $PSScriptRoot "backend\launcher.py"
        }
        if (Test-Path $launcher) {
            $output = & $PythonExe $launcher --reset-app-data --confirm DELETE --backup-dest $emergencyBackup 2>&1
            $exitCode = $LASTEXITCODE
        } else {
            Write-Host "ERROR: Launcher not found at $launcher" -ForegroundColor Red
            return
        }
    } else {
        Write-Host "ERROR: Neither AttendPlan.exe nor Python runtime found. Cannot safely execute reset." -ForegroundColor Red
        return
    }

    # Print canonical engine output
    foreach ($line in $output) {
        Write-Host "  $line" -ForegroundColor Gray
    }

    # Handle structured engine result states
    switch ($exitCode) {
        0 {
            Write-Host "`n==================================================================" -ForegroundColor Green
            Write-Host "  RESULT: SUCCESS — APPLICATION DATA RESET COMPLETED SAFELY" -ForegroundColor Green
            Write-Host "==================================================================" -ForegroundColor Green
            Write-Host "  Emergency Backup Preserved : $emergencyBackup" -ForegroundColor Green
            Write-Host "  Historical Backups Kept    : $BackupsDir" -ForegroundColor Cyan
            Write-Host "  Security Evidence Kept     : $EvidenceDir" -ForegroundColor Magenta
            Write-Host "==================================================================" -ForegroundColor Green
        }
        2 {
            Write-Host "`nRESULT: CANCELLED — Reset confirmation was not provided. No files were modified." -ForegroundColor Green
        }
        3 {
            Write-Host "`nCRITICAL SAFETY ABORT: BACKUP_FAILED" -ForegroundColor Red
            Write-Host "Safety backup failed or failed integrity verification." -ForegroundColor Red
            Write-Host "The database and local data were NOT modified. Your data remains untouched." -ForegroundColor Red
        }
        4 {
            Write-Host "`nCRITICAL SAFETY ABORT: VAULT_FAILED" -ForegroundColor Red
            Write-Host "Failed to revoke credentials in Windows Credential Manager." -ForegroundColor Red
            Write-Host "Reset was aborted before any data deletion. Your data remains untouched." -ForegroundColor Red
        }
        5 {
            Write-Host "`nCRITICAL SAFETY ABORT: APP_RUNNING" -ForegroundColor Red
            Write-Host "AttendPlan is currently running or database is locked." -ForegroundColor Red
            Write-Host "Please close AttendPlan and retry." -ForegroundColor Red
        }
        6 {
            Write-Host "`nWARNING: DELETION_PARTIAL" -ForegroundColor Yellow
            Write-Host "Some allowlisted files or directories could not be deleted (they may be in use)." -ForegroundColor Yellow
            Write-Host "Verified emergency backup remains preserved at: $emergencyBackup" -ForegroundColor Green
        }
        7 {
            Write-Host "`nCRITICAL SAFETY ABORT: INVALID_PATH" -ForegroundColor Red
            Write-Host "Backup destination or application data directory path is invalid." -ForegroundColor Red
            Write-Host "No files were modified." -ForegroundColor Red
        }
        default {
            Write-Host "`nCRITICAL SAFETY ABORT: UNEXPECTED_ERROR (Exit Code: $exitCode)" -ForegroundColor Red
            Write-Host "An unexpected error occurred during reset. Check logs for details." -ForegroundColor Red
        }
    }
}

if ($NonInteractive) {
    Invoke-IntegrityCheck
    exit 0
}

# Interactive Menu Loop
do {
    Show-Header
    Write-Host " Select an option:" -ForegroundColor White
    Write-Host "  [1] Storage Health & Database Integrity Check"
    Write-Host "  [2] Create Verified Safety Backup (SQLite Online Engine)"
    Write-Host "  [3] Clean Temporary Cache & Profile Data (Preserves Database & Settings)"
    Write-Host "  [4] Standard Safe Program Uninstall (Preserves All User Data)"
    Write-Host "  [5] Full Application Data Reset (Requires 'DELETE' & Verified Backup)"
    Write-Host "  [0] Exit"
    Write-Host ""
    $choice = Read-Host "Enter selection [0-5]"

    switch ($choice) {
        "1" { Invoke-IntegrityCheck; Read-Host "`nPress Enter to return to menu..." }
        "2" { Invoke-SafetyBackup | Out-Null; Read-Host "`nPress Enter to return to menu..." }
        "3" { Invoke-CacheCleanup; Read-Host "`nPress Enter to return to menu..." }
        "4" { Invoke-StandardUninstall; Read-Host "`nPress Enter to return to menu..." }
        "5" { Invoke-FullReset; Read-Host "`nPress Enter to return to menu..." }
        "0" { Write-Host "`nExiting maintenance utility. Goodbye!" -ForegroundColor Cyan; break }
        default { Write-Host "Invalid choice. Please select 0 to 5." -ForegroundColor Red; Start-Sleep -Seconds 1 }
    }
} while ($choice -ne "0")
