[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$StartScript = Join-Path $PSScriptRoot "start-backend.ps1"
$StartupDirectory = [Environment]::GetFolderPath("Startup")
$EntryPath = Join-Path $StartupDirectory "Docling Local Engine.cmd"
$Content = "@echo off`r`npowershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$StartScript`" -Background`r`n"
Set-Content -LiteralPath $EntryPath -Value $Content -Encoding ascii
Write-Host "Installed Docling auto-start for the current Windows user." -ForegroundColor Green
Write-Host "Entry: $EntryPath"
