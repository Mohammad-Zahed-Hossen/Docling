[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$BackendDirectory = Join-Path $RepositoryRoot "backend"
$env:UV_CACHE_DIR = Join-Path $RepositoryRoot ".uv-cache"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Error: uv is not installed or is not available on PATH." -ForegroundColor Red
    Write-Host "Install uv from https://docs.astral.sh/uv/ and try again."
    exit 1
}

if (-not (Test-Path -LiteralPath (Join-Path $BackendDirectory "pyproject.toml"))) {
    Write-Host "Error: backend/pyproject.toml was not found." -ForegroundColor Red
    exit 1
}

Write-Host "Starting Docling Local Engine at http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "Keep this window open. Press Ctrl+C to stop the engine."
Push-Location -LiteralPath $BackendDirectory
try {
    uv run python -m docling_api
    if ($LASTEXITCODE -ne 0) { throw "The backend exited with code $LASTEXITCODE." }
}
catch {
    Write-Host "Failed to start Docling Local Engine: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
finally {
    Pop-Location
}
