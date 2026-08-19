@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
:menu
cls
echo Docling Local Engine
echo ====================
echo 1. Status
echo 2. Start
echo 3. Stop
echo 4. Restart
echo 5. Exit
choice /C 12345 /N /M "Choose an action: "
if errorlevel 5 exit /b 0
if errorlevel 4 powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%restart-backend.ps1"
if errorlevel 3 powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%stop-backend.ps1"
if errorlevel 2 powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%start-backend.ps1" -Background
if errorlevel 1 powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%status-backend.ps1"
echo.
pause
goto menu
