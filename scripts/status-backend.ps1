[CmdletBinding()]
param()

$ErrorActionPreference = "SilentlyContinue"
$Health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" -TimeoutSec 2
if ($Health.status -eq "ok" -and $Health.service -eq "unified-markdown-converter") {
    Write-Host "Unified Markdown Converter is running at http://127.0.0.1:8000" -ForegroundColor Green
    exit 0
}

Write-Host "Unified Markdown Converter is not running." -ForegroundColor Yellow
exit 1
