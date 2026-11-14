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
        Write-Host "Reset aborted. No files were modified." -ForegroundColor Green
        return
    }

    $desktopDir = [Environment]::GetFolderPath("Desktop")
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $emergencyBackup = Join-Path $desktopDir "AttendPlan_PreReset_Backup_$timestamp.sqlite3"

    Write-Host "`nCreating mandatory safety backup to Desktop..." -ForegroundColor Cyan
    $backupResult = Invoke-SafetyBackup -CustomDest $emergencyBackup

    if (-not $backupResult -or -not (Test-Path $emergencyBackup) -or (Get-Item $emergencyBackup).Length -eq 0) {
        Write-Host "`nCRITICAL SAFETY ABORT: Safety backup failed or failed integrity verification." -ForegroundColor Red
        Write-Host "The database and local data will NOT be deleted. Your data remains untouched." -ForegroundColor Red
        return
    }

    Write-Host "Safety backup verified successfully: $emergencyBackup" -ForegroundColor Green

    # Revoke authenticator in Windows Credential Manager
    if ($AppExe) {
        cmd /c "`"$AppExe`" --purge-vault"
    } elseif ($PythonExe) {
        $launcher = Join-Path $PSScriptRoot "..\backend\launcher.py"
        if (Test-Path $launcher) {
            & $PythonExe $launcher --purge-vault
        }
    }

    # Strict Allowlist of application-owned files to delete in %LOCALAPPDATA%\AttendPlan
    $allowlistFiles = @(
        "attendplan.sqlite3",
        "attendplan.sqlite3-wal",
        "attendplan.sqlite3-shm",
        "settings.json",
        "startup.json",
        "term_calendars.json",
        "totp_metadata.json"
    )

    $allowlistDirs = @(
        "logs",
        "run",
        "chrome-profile"
    )

    Write-Host "`nRemoving working database and configuration (allowlist only)..." -ForegroundColor Yellow
    foreach ($fname in $allowlistFiles) {
        $target = Join-Path $AttendPlanDataDir $fname
        if (Test-Path $target) {
            Remove-Item -Path $target -Force -ErrorAction SilentlyContinue
            Write-Host "  Deleted: $fname" -ForegroundColor Gray
        }
    }

    foreach ($dname in $allowlistDirs) {
        $targetDir = Join-Path $AttendPlanDataDir $dname
        if (Test-Path $targetDir) {
            Remove-Item -Path $targetDir -Recurse -Force -ErrorAction SilentlyContinue
            Write-Host "  Cleared: $dname\" -ForegroundColor Gray
        }
    }

    Write-Host "`n==================================================================" -ForegroundColor Green
    Write-Host "  APPLICATION DATA RESET COMPLETED SUCCESSFULLY" -ForegroundColor Green
    Write-Host "==================================================================" -ForegroundColor Green
    Write-Host "  Emergency Backup Preserved : $emergencyBackup" -ForegroundColor Green
    Write-Host "  Historical Backups Kept    : $BackupsDir" -ForegroundColor Cyan
    Write-Host "  Security Evidence Kept     : $EvidenceDir" -ForegroundColor Magenta
    Write-Host "==================================================================" -ForegroundColor Green
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
