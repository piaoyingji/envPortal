param(
    [string]$InstallDir = "C:\EnvPortal",
    [string]$ServiceName = "EnvPortal",
    [string]$DisplayName = "EnvPortal",
    [string]$NssmPath = ""
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path (Join-Path $InstallDir "run.py"))) {
    throw "run.py was not found under InstallDir: $InstallDir"
}

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCommand) {
    $pythonCommand = Get-Command py -ErrorAction Stop
}
$pythonExe = $pythonCommand.Source
$pythonArgs = if ((Split-Path -Leaf $pythonExe).ToLowerInvariant() -eq "py.exe") {
    "-3 `"$InstallDir\run.py`""
} else {
    "`"$InstallDir\run.py`""
}

if (-not $NssmPath) {
    $candidatePaths = @(
        (Join-Path $InstallDir "tools\nssm.exe"),
        "C:\Tools\nssm\nssm.exe",
        "C:\nssm\nssm.exe"
    )
    $NssmPath = $candidatePaths | Where-Object { Test-Path $_ } | Select-Object -First 1
}

if ($NssmPath -and (Test-Path $NssmPath)) {
    $existing = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if (-not $existing) {
        & $NssmPath install $ServiceName $pythonExe $pythonArgs
    }
    & $NssmPath set $ServiceName AppDirectory $InstallDir
    & $NssmPath set $ServiceName DisplayName $DisplayName
    & $NssmPath set $ServiceName Start SERVICE_AUTO_START
    & $NssmPath set $ServiceName AppStdout (Join-Path $InstallDir "logs\envportal-service.out.log")
    & $NssmPath set $ServiceName AppStderr (Join-Path $InstallDir "logs\envportal-service.err.log")
    & $NssmPath set $ServiceName AppRotateFiles 1
    & $NssmPath set $ServiceName AppRotateBytes 10485760
    New-Item -ItemType Directory -Force -Path (Join-Path $InstallDir "logs") | Out-Null
    Start-Service $ServiceName
    Write-Host "Windows service installed and started: $ServiceName"
    exit 0
}

$taskName = "$ServiceName Startup"
$action = New-ScheduledTaskAction -Execute $pythonExe -Argument $pythonArgs -WorkingDirectory $InstallDir
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName $taskName
Write-Host "NSSM was not found. Registered startup scheduled task instead: $taskName"
