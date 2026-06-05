param(
    [string]$ListenPrefix = "http://+:8998/",
    [string]$TargetBaseUrl = "http://192.168.20.38:8999/",
    [string]$ServiceName = "EnvPortalDomainProxy",
    [string]$DisplayName = "EnvPortal Domain Proxy",
    [string]$InstallDir = "C:\EnvPortalDomainProxy"
)

$ErrorActionPreference = "Stop"

function Test-Admin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-Admin)) {
    $script = $PSCommandPath
    $args = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "`"$script`"",
        "-ListenPrefix", "`"$ListenPrefix`"",
        "-TargetBaseUrl", "`"$TargetBaseUrl`"",
        "-ServiceName", "`"$ServiceName`"",
        "-DisplayName", "`"$DisplayName`"",
        "-InstallDir", "`"$InstallDir`""
    )
    Start-Process powershell.exe -ArgumentList $args -Verb RunAs
    Write-Host "Elevation requested. Continue in the elevated PowerShell window."
    exit 0
}

$repo = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$project = Join-Path $repo "tools\domain-proxy\EnvPortal.DomainProxy.csproj"
$publish = Join-Path $repo "tools\domain-proxy\publish"

dotnet publish $project -c Release -r win-x64 --self-contained false -o $publish

$exe = Join-Path $InstallDir "EnvPortal.DomainProxy.exe"
if (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue) {
    Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
    $deadline = (Get-Date).AddSeconds(20)
    do {
        $svc = Get-CimInstance Win32_Service -Filter "Name='$ServiceName'" -ErrorAction SilentlyContinue
        if (-not $svc -or $svc.State -eq "Stopped") { break }
        Start-Sleep -Milliseconds 500
    } while ((Get-Date) -lt $deadline)
    sc.exe delete $ServiceName | Out-Null
    Start-Sleep -Seconds 2
}

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Copy-Item -Path (Join-Path $publish "*") -Destination $InstallDir -Recurse -Force

$settings = @{
    Proxy = @{
        ListenPrefix = $ListenPrefix
        TargetBaseUrl = $TargetBaseUrl
        HeaderName = "X-Remote-User"
        AllowedUsersFile = "allowed-users.txt"
        CorsAllowedOrigins = "http://192.168.20.38:8999,http://localhost:8999"
    }
} | ConvertTo-Json -Depth 4
$settings | Set-Content -Path (Join-Path $InstallDir "appsettings.json") -Encoding UTF8

$currentUser = whoami /upn
if (-not $currentUser) { $currentUser = whoami }
$currentUser | Set-Content -Path (Join-Path $InstallDir "allowed-users.txt") -Encoding UTF8

$url = $ListenPrefix
netsh http delete urlacl url=$url 2>$null | Out-Null
netsh http add urlacl url=$url user="NT AUTHORITY\Authenticated Users" | Out-Null

$port = ([uri]($ListenPrefix -replace "\+", "localhost")).Port
if ($port -gt 0) {
    $ruleName = "EnvPortal Domain Proxy $port"
    if (-not (Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue)) {
        New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort $port | Out-Null
    }
}

New-Service -Name $ServiceName -DisplayName $DisplayName -BinaryPathName "`"$exe`"" -StartupType Automatic | Out-Null
Start-Service -Name $ServiceName

Write-Host "Installed $DisplayName"
Write-Host "Listen: $ListenPrefix"
Write-Host "Target: $TargetBaseUrl"
Write-Host "Allowed users file: $(Join-Path $InstallDir "allowed-users.txt")"
