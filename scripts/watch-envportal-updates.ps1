param(
    [string]$InstallDir = "C:\workspace\envPortal",
    [string]$Branch = "main",
    [string]$ServiceName = "EnvPortal",
    [string]$LogFile = ""
)

$ErrorActionPreference = "Stop"

if (-not $LogFile) {
    $LogFile = Join-Path $InstallDir "logs\envportal-auto-update.log"
}

$logDir = Split-Path -Parent $LogFile
if ($logDir -and -not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
}

function Write-DeployLog($Message) {
    $line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -LiteralPath $LogFile -Value $line -Encoding UTF8
}

Set-Location $InstallDir

$lockFile = Join-Path $InstallDir ".envportal-update.lock"
$lockStream = $null
try {
    $lockStream = [System.IO.File]::Open($lockFile, [System.IO.FileMode]::OpenOrCreate, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
} catch {
    Write-DeployLog "Another updater is already running; skipped."
    exit 0
}

try {
    $current = (git rev-parse HEAD).Trim()
    git fetch origin $Branch | Out-Null
    $remote = (git rev-parse "origin/$Branch").Trim()

    if ($current -eq $remote) {
        Write-DeployLog "No update. HEAD=$current"
        exit 0
    }

    Write-DeployLog "Updating $current -> $remote from origin/$Branch"
    git pull --ff-only origin $Branch | Out-Null

    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($service) {
        Restart-Service -Name $ServiceName -Force
        Write-DeployLog "Restarted service $ServiceName."
    } else {
        Write-DeployLog "Service $ServiceName was not found; update completed without restart."
    }
} catch {
    Write-DeployLog "ERROR: $($_.Exception.Message)"
    throw
} finally {
    if ($lockStream) {
        $lockStream.Dispose()
    }
}
