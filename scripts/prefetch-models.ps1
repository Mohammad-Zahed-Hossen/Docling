[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$BackendDirectory = Join-Path $RepositoryRoot "backend"
$env:UV_CACHE_DIR = Join-Path $RepositoryRoot ".uv-cache"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Error: uv is not installed or is not available on PATH." -ForegroundColor Red
    exit 1
}

Push-Location -LiteralPath $BackendDirectory
try {
    Write-Host "Prefetching the CPU models used by Docling..."
    uv run docling-tools models download layout tableformer rapidocr
    if ($LASTEXITCODE -ne 0) { throw "Model prefetch exited with code $LASTEXITCODE." }
    Write-Host "Docling models are cached for later starts." -ForegroundColor Green
}
finally {
    Pop-Location
}
