@echo off
setlocal
title AttendPlan Full Application Launcher

:: Resolve script directory with trailing backslash
set "SCRIPT_DIR=%~dp0"
set "ATTENDPLAN_ENV=development"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%scripts\Launch-AttendPlan.ps1" %*
if errorlevel 1 (
    echo.
    echo ==========================================
    echo [ERROR] Launch-AttendPlan encountered an error.
    echo ==========================================
    echo.
    pause
    exit /b 1
)

exit /b 0
