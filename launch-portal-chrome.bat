@echo off
title AttendPlan Dedicated Chrome Launcher
echo ===================================================
echo Launching Dedicated AttendPlan Chrome with CDP...
echo ===================================================

set "CHROME_EXE=C:\Program Files\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME_EXE%" set "CHROME_EXE=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME_EXE%" set "CHROME_EXE=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"

set "PROFILE_DIR=%LOCALAPPDATA%\AttendPlan\chrome-profile"

if not exist "%PROFILE_DIR%" mkdir "%PROFILE_DIR%"

start "" "%CHROME_EXE%" --remote-debugging-port=9222 --remote-debugging-address=127.0.0.1 --user-data-dir="%PROFILE_DIR%" --no-first-run --no-default-browser-check "https://mrei.icloudems.com/corecampus/index.php"

echo Chrome launched on 127.0.0.1:9222!
