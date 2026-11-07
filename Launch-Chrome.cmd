@echo off
setlocal
title AttendPlan Dedicated Chrome Launcher

:: Resolve script directory with trailing backslash
set "SCRIPT_DIR=%~dp0"

echo ==========================================
echo       ATTENDPLAN CHROME LAUNCHER
echo      Dedicated Browser with CDP
echo ==========================================
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%scripts\Launch-Chrome.ps1" %*
if errorlevel 1 (
    echo.
    echo ==========================================
    echo [ERROR] Launch-Chrome encountered an error.
    echo ==========================================
    echo.
    pause
    exit /b 1
)

exit /b 0
