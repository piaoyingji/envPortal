param(
    [string]$InstallDir = "C:\workspace\envPortal",
    [string]$Branch = "main",
    [string]$ServiceName = "EnvPortal",
    [string]$TaskName = "EnvPortal Auto Update"
)

$ErrorActionPreference = "Stop"

$watcher = Join-Path $InstallDir "scripts\watch-envportal-updates.ps1"
if (-not (Test-Path $watcher)) {
    throw "Update watcher script was not found: $watcher"
}

$powershell = (Get-Command powershell.exe -ErrorAction Stop).Source
$arguments = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$watcher`"",
    "-InstallDir", "`"$InstallDir`"",
    "-Branch", "`"$Branch`"",
    "-ServiceName", "`"$ServiceName`""
) -join " "

$action = New-ScheduledTaskAction -Execute $powershell -Argument $arguments -WorkingDirectory $InstallDir
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).Date -RepetitionInterval (New-TimeSpan -Minutes 1) -RepetitionDuration ([TimeSpan]::MaxValue)
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 10) -StartWhenAvailable

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName $TaskName

Write-Host "Registered auto update task: $TaskName"
Write-Host "Branch: origin/$Branch"
Write-Host "InstallDir: $InstallDir"
