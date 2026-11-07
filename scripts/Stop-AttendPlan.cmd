@echo off
setlocal
title AttendPlan Service Shutdown Helper
set "SCRIPT_DIR=%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%Stop-AttendPlan.ps1"
echo.
pause
