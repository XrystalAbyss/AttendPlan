@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0AttendPlan-Maintenance.ps1"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo AttendPlan Maintenance finished with code %ERRORLEVEL%.
    pause
)
