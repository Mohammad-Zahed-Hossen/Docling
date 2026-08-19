[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$PidFile = Join-Path $RepositoryRoot "runtime\backend.pid"

if (-not (Test-Path -LiteralPath $PidFile)) {
    Write-Host "No managed Docling backend PID was found." -ForegroundColor Yellow
    exit 0
}

$BackendPid = [int](Get-Content -Raw -LiteralPath $PidFile)
$Process = Get-CimInstance Win32_Process -Filter "ProcessId = $BackendPid" -ErrorAction SilentlyContinue
if ($null -eq $Process) {
    Remove-Item -LiteralPath $PidFile -Force
    Write-Host "The recorded Docling backend is no longer running. Removed stale PID file."
    exit 0
}
if ($Process.Name -ne "uv.exe" -or $Process.CommandLine -notmatch "run\s+python\s+-m\s+docling_api") {
    Write-Host "PID $BackendPid no longer belongs to the managed Docling backend; nothing was stopped." -ForegroundColor Red
    exit 1
}

& taskkill.exe /PID $BackendPid /T /F | Out-Null
Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
Write-Host "Docling Local Engine stopped." -ForegroundColor Green
