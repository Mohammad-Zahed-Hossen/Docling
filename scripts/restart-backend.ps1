[CmdletBinding()]
param()

$StopScript = Join-Path $PSScriptRoot "stop-backend.ps1"
$StartScript = Join-Path $PSScriptRoot "start-backend.ps1"
& $StopScript
& $StartScript -Background
exit $LASTEXITCODE
