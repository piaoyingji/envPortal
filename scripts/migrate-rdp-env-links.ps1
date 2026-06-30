param(
    [string]$BaseDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [switch]$DryRun,
    [switch]$ReportJson,
    [switch]$FailOnDirty
)

$ErrorActionPreference = "Stop"
$utf8 = New-Object System.Text.UTF8Encoding $false
[Console]::OutputEncoding = $utf8
$OutputEncoding = $utf8

$pythonArgs = @((Join-Path $PSScriptRoot "migrate_rdp_env_links.py"), "--base-dir", $BaseDir)
if ($DryRun) { $pythonArgs += "--dry-run" }
if ($ReportJson) { $pythonArgs += "--report-json" }
if ($FailOnDirty) { $pythonArgs += "--fail-on-dirty" }

$py = Get-Command py -ErrorAction SilentlyContinue
if ($py) {
    & py -3 @pythonArgs
} else {
    $python = Get-Command python -ErrorAction Stop
    & $python.Source @pythonArgs
}

exit $LASTEXITCODE
