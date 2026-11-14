# AttendPlan — Maintenance, Diagnostics, and Storage Recovery
# Provides safe management of local database, caches, backups, and resets.
param(
    [switch]$NonInteractive = $false
)

$ErrorActionPreference = "Stop"

$AppDataLocal = if ($env:LOCALAPPDATA) { $env:LOCALAPPDATA } else { Join-Path $env:USERPROFILE "AppData\Local" }
$AttendPlanDataDir = Join-Path $AppDataLocal "AttendPlan"
$DbPath = Join-Path $AttendPlanDataDir "attendplan.sqlite3"
$SettingsPath = Join-Path $AttendPlanDataDir "settings.json"
$BackupsDir = Join-Path $AttendPlanDataDir "backups"

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
    Write-Host "  AttendPlan — Maintenance, Diagnostics & Storage Utility" -ForegroundColor Cyan
    Write-Host "==================================================================" -ForegroundColor Cyan
    Write-Host " Data Directory : $AttendPlanDataDir"
    Write-Host " Database File  : $DbPath"
    if (Test-Path $DbPath) {
        $size = (Get-Item $DbPath).Length
        Write-Host " Database Status: PRESENT ($([math]::Round($size / 1MB, 2)) MB)" -ForegroundColor Green
    } else {
        Write-Host " Database Status: NOT FOUND" -ForegroundColor Yellow
    }
    if (Test-Path $SettingsPath) {
        Write-Host " Settings File  : PRESENT" -ForegroundColor Green
    } else {
        Write-Host " Settings File  : NOT FOUND" -ForegroundColor Yellow
    }
    Write-Host "==================================================================" -ForegroundColor Cyan
}

function Invoke-IntegrityCheck {
    Write-Host "`n[1] Running Storage Health & Integrity Check..." -ForegroundColor Yellow
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
        Write-Host "`nSettings Overview:" -ForegroundColor Gray
        try {
            $raw = Get-Content $SettingsPath -Raw | ConvertFrom-Json
            Write-Host "  Has Saved Mobile: $($raw.has_saved_mobile)"
            Write-Host "  Masked Mobile   : $($raw.masked_mobile)"
            Write-Host "  Auto Continuation: $($raw.auto_login_continuation)"
        } catch {
            Write-Host "  Failed to read settings.json: $_" -ForegroundColor Red
        }
    }
}

function Invoke-SafetyBackup {
    Write-Host "`n[2] Creating Consistent Safety Backup..." -ForegroundColor Yellow
    if (-not (Test-Path $DbPath)) {
        Write-Host "ERROR: No database file found to backup." -ForegroundColor Red
        return
    }

    if (-not (Test-Path $BackupsDir)) {
        New-Item -ItemType Directory -Path $BackupsDir -Force | Out-Null
    }

    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupDest = Join-Path $BackupsDir "attendplan_backup_$timestamp.sqlite3"

    if ($AppExe) {
        Write-Host "Using AttendPlan CLI engine..." -ForegroundColor Gray
        cmd /c "`"$AppExe`" --backup-db `"$backupDest`""
    } elseif ($PythonExe) {
        $launcher = Join-Path $PSScriptRoot "..\backend\launcher.py"
        if (Test-Path $launcher) {
            Write-Host "Using Python launcher backup engine..." -ForegroundColor Gray
            & $PythonExe $launcher --backup-db $backupDest
        }
    } else {
        Copy-Item -Path $DbPath -Destination $backupDest -Force
        $hash = (Get-FileHash -Path $backupDest -Algorithm SHA256).Hash
        Write-Host "BACKUP_SUCCESS: $backupDest" -ForegroundColor Green
        Write-Host "SHA256: $hash"
        Write-Host "SIZE: $((Get-Item $backupDest).Length) bytes"
    }
}

function Invoke-CacheCleanup {
    Write-Host "`n[3] Cleaning Regenerable Temporary Caches..." -ForegroundColor Yellow
    Write-Host "NOTE: Saved database, academic history, and settings will NOT be touched." -ForegroundColor Gray

    $cacheDirs = @(
        (Join-Path $AttendPlanDataDir "chrome_profile\Default\Cache"),
        (Join-Path $AttendPlanDataDir "chrome_profile\Default\Code Cache"),
        (Join-Path $AttendPlanDataDir "chrome_profile\Default\DawnGraphiteCache"),
        (Join-Path $AttendPlanDataDir "chrome_profile\Default\GPUCache")
    )

    $cleanedCount = 0
    foreach ($dir in $cacheDirs) {
        if (Test-Path $dir) {
            try {
                Remove-Item -Path "$dir\*" -Recurse -Force -ErrorAction SilentlyContinue
                Write-Host "Cleaned: $dir" -ForegroundColor Green
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
            Write-Host "Cleaned: $logsDir log files" -ForegroundColor Green
            $cleanedCount++
        } catch {
            Write-Host "Warning: Could not clean logs directory" -ForegroundColor Yellow
        }
    }

    Write-Host "`nCache cleanup finished ($cleanedCount locations processed)." -ForegroundColor Green
}

function Invoke-StandardUninstall {
    Write-Host "`n[4] Standard Safe Uninstallation..." -ForegroundColor Yellow
    $regKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{C6B5E87D-1F33-4D91-8846-9D923E2A3819}_is1"
    if (Test-Path $regKey) {
        $uninstaller = (Get-ItemProperty -Path $regKey).UninstallString
        if ($uninstaller) {
            Write-Host "Found registered uninstaller: $uninstaller" -ForegroundColor Cyan
            Write-Host "Launching official uninstaller..." -ForegroundColor Green
            Start-Process -FilePath $uninstaller
            return
        }
    }
    Write-Host "No registered Inno Setup uninstaller found in user registry." -ForegroundColor Yellow
}

function Invoke-FullReset {
    Write-Host "`n[5] FULL CLEAN RESET / STORAGE PURGE" -ForegroundColor Red
    Write-Host "WARNING: This will permanently erase your local database, courses, and settings." -ForegroundColor Red
    Write-Host "An emergency safety backup will be automatically saved to your Desktop before removal." -ForegroundColor Yellow

    $confirm = Read-Host "`nType 'DELETE' in capital letters to proceed with full local data reset"
    if ($confirm -ne "DELETE") {
        Write-Host "Reset aborted. No files were modified." -ForegroundColor Green
        return
    }

    # Emergency backup
    if (Test-Path $DbPath) {
        $desktopDir = [Environment]::GetFolderPath("Desktop")
        $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $emergencyBackup = Join-Path $desktopDir "AttendPlan_Emergency_Backup_$timestamp.sqlite3"
        Copy-Item -Path $DbPath -Destination $emergencyBackup -Force
        Write-Host "Emergency pre-reset backup saved to: $emergencyBackup" -ForegroundColor Green
    }

    # Verify path safety before deleting
    if ($AttendPlanDataDir.EndsWith("AttendPlan") -and (Test-Path $AttendPlanDataDir)) {
        Write-Host "Removing local storage directory: $AttendPlanDataDir..." -ForegroundColor Yellow
        try {
            Remove-Item -Path $AttendPlanDataDir -Recurse -Force
            Write-Host "Local AttendPlan storage successfully cleared." -ForegroundColor Green
        } catch {
            Write-Host "Error clearing storage: $_" -ForegroundColor Red
        }
    } else {
        Write-Host "Safety check prevented deletion: Path does not end with 'AttendPlan'" -ForegroundColor Red
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
    Write-Host "  [2] Create Immediate Consistent Safety Backup"
    Write-Host "  [3] Clean Temporary Cache & Profile Data (Preserves Database)"
    Write-Host "  [4] Standard Safe Uninstall (Preserves Database & Settings)"
    Write-Host "  [5] Full Clean Reset (Erases Local Data — Requires Typed Confirmation)"
    Write-Host "  [0] Exit"
    Write-Host ""
    $choice = Read-Host "Enter selection [0-5]"

    switch ($choice) {
        "1" { Invoke-IntegrityCheck; Read-Host "`nPress Enter to return to menu..." }
        "2" { Invoke-SafetyBackup; Read-Host "`nPress Enter to return to menu..." }
        "3" { Invoke-CacheCleanup; Read-Host "`nPress Enter to return to menu..." }
        "4" { Invoke-StandardUninstall; Read-Host "`nPress Enter to return to menu..." }
        "5" { Invoke-FullReset; Read-Host "`nPress Enter to return to menu..." }
        "0" { Write-Host "`nExiting maintenance utility. Goodbye!" -ForegroundColor Cyan; break }
        default { Write-Host "Invalid choice. Please select 0 to 5." -ForegroundColor Red; Start-Sleep -Seconds 1 }
    }
} while ($choice -ne "0")
