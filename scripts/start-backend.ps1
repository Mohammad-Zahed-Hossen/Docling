[CmdletBinding()]
param([switch]$Background)

$ErrorActionPreference = "Stop"
$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$BackendDirectory = Join-Path $RepositoryRoot "backend"
$env:UV_CACHE_DIR = Join-Path $RepositoryRoot ".uv-cache"
$env:HOST = "127.0.0.1"
$env:PORT = "8000"
$RuntimeDirectory = Join-Path $RepositoryRoot "runtime"
$PidFile = Join-Path $RuntimeDirectory "backend.pid"
$LogFile = Join-Path $RuntimeDirectory "backend.log"
$OutputLogFile = Join-Path $RuntimeDirectory "backend-output.log"

function Test-EngineHealth {
    try {
        $Health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" -TimeoutSec 2
        return $Health.status -eq "ok" -and $Health.service -eq "unified-markdown-converter"
    }
    catch { return $false }
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Error: uv is not installed or is not available on PATH." -ForegroundColor Red
    Write-Host "Install uv from https://docs.astral.sh/uv/ and try again."
    exit 1
}

if (-not (Test-Path -LiteralPath (Join-Path $BackendDirectory "pyproject.toml"))) {
    Write-Host "Error: backend/pyproject.toml was not found." -ForegroundColor Red
    exit 1
}

if (Test-EngineHealth) {
    Write-Host "Unified Markdown Converter is already running at http://127.0.0.1:8000" -ForegroundColor Green
    exit 0
}

if ($Background) {
    New-Item -ItemType Directory -Path $RuntimeDirectory -Force | Out-Null
    $UvCmd = Get-Command uv -ErrorAction SilentlyContinue
    $UvPath = if ($UvCmd) { $UvCmd.Source } else { "uv" }
    $Process = Start-Process -FilePath $UvPath `
        -ArgumentList @("run", "python", "-m", "docling_api") `
        -WorkingDirectory $BackendDirectory `
        -WindowStyle Hidden `
        -RedirectStandardOutput $OutputLogFile `
        -RedirectStandardError $LogFile `
        -PassThru
    Set-Content -LiteralPath $PidFile -Value $Process.Id -Encoding ascii

    for ($Attempt = 0; $Attempt -lt 60; $Attempt++) {
        if (Test-EngineHealth) {
            Write-Host "Unified Markdown Converter started in the background." -ForegroundColor Green
            Write-Host "Logs: $LogFile"
            exit 0
        }
        if ($Process.HasExited) { break }
        Start-Sleep -Milliseconds 500
    }
    Write-Host "Unified Markdown Converter did not become ready. Check $LogFile" -ForegroundColor Red
    exit 1
}

Write-Host "Starting Unified Markdown Converter at http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "Keep this window open. Press Ctrl+C to stop the engine."
Push-Location -LiteralPath $BackendDirectory
try {
    uv run python -m docling_api
    if ($LASTEXITCODE -ne 0) { throw "The backend exited with code $LASTEXITCODE." }
}
catch {
    Write-Host "Failed to start Unified Markdown Converter: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
finally {
    Pop-Location
}
