[CmdletBinding()]
param()

$StartupDirectory = [Environment]::GetFolderPath("Startup")
$EntryPath = Join-Path $StartupDirectory "Docling Local Engine.cmd"
if (Test-Path -LiteralPath $EntryPath) {
    Remove-Item -LiteralPath $EntryPath -Force
    Write-Host "Removed Docling auto-start." -ForegroundColor Green
} else {
    Write-Host "Docling auto-start was not installed."
}
