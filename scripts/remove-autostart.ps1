[CmdletBinding()]
param()

$StartupDirectory = [Environment]::GetFolderPath("Startup")
$CmdEntryPath = Join-Path $StartupDirectory "Docling Local Engine.cmd"
$VbsEntryPath = Join-Path $StartupDirectory "Docling Local Engine.vbs"

$Removed = $false
if (Test-Path -LiteralPath $CmdEntryPath) {
    Remove-Item -LiteralPath $CmdEntryPath -Force
    $Removed = $true
}
if (Test-Path -LiteralPath $VbsEntryPath) {
    Remove-Item -LiteralPath $VbsEntryPath -Force
    $Removed = $true
}

if ($Removed) {
    Write-Host "Removed Docling auto-start." -ForegroundColor Green
} else {
    Write-Host "Docling auto-start was not installed."
}
