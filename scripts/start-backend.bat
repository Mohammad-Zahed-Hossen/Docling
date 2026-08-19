@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%start-backend.ps1"
if errorlevel 1 (
  echo.
  echo Docling Local Engine did not start successfully.
  pause
  exit /b 1
)
endlocal
