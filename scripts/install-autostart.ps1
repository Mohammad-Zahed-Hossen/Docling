[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$StartScript = Join-Path $PSScriptRoot "start-backend.ps1"
$StartupDirectory = [Environment]::GetFolderPath("Startup")
$CmdEntryPath = Join-Path $StartupDirectory "Docling Local Engine.cmd"
if (Test-Path -LiteralPath $CmdEntryPath) {
    Remove-Item -LiteralPath $CmdEntryPath -Force
}

$VbsEntryPath = Join-Path $StartupDirectory "Docling Local Engine.vbs"
$VbsContent = "Set WshShell = CreateObject(`"WScript.Shell`")`r`nWshShell.Run `"powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"`"$StartScript`"`" -Background`", 0, False`r`n"
Set-Content -LiteralPath $VbsEntryPath -Value $VbsContent -Encoding ascii
Write-Host "Installed silent Docling auto-start for the current Windows user." -ForegroundColor Green
Write-Host "Entry: $VbsEntryPath"
