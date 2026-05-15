param(
    [string]$ComputerName = "192.168.20.38",
    [string]$UserName = "Administrator",
    [string]$RepoUrl = "https://github.com/piaoyingji/envPortal.git",
    [string]$Branch = "main",
    [string]$InstallDir = "C:\EnvPortal"
)

$ErrorActionPreference = "Stop"

$cred = Get-Credential -UserName $UserName -Message "Credential for $ComputerName"

Set-Item WSMan:\localhost\Client\TrustedHosts -Value $ComputerName -Concatenate -Force

$session = New-PSSession -ComputerName $ComputerName -Credential $cred
try {
    Invoke-Command -Session $session -ScriptBlock {
        param($RepoUrl, $Branch, $InstallDir)
        if (-not (Test-Path $InstallDir)) {
            New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
        }
    } -ArgumentList $RepoUrl, $Branch, $InstallDir

    $remoteScripts = Join-Path $InstallDir "scripts"
    Invoke-Command -Session $session -ScriptBlock {
        param($RemoteScripts)
        New-Item -ItemType Directory -Force -Path $RemoteScripts | Out-Null
    } -ArgumentList $remoteScripts

    Copy-Item -ToSession $session -Path "$PSScriptRoot\update-envportal.ps1" -Destination $remoteScripts -Force
    Copy-Item -ToSession $session -Path "$PSScriptRoot\install-envportal-service.ps1" -Destination $remoteScripts -Force

    Invoke-Command -Session $session -ScriptBlock {
        param($RepoUrl, $Branch, $InstallDir)
        & (Join-Path $InstallDir "scripts\update-envportal.ps1") -RepoUrl $RepoUrl -Branch $Branch -InstallDir $InstallDir
        & (Join-Path $InstallDir "scripts\install-envportal-service.ps1") -InstallDir $InstallDir
    } -ArgumentList $RepoUrl, $Branch, $InstallDir
} finally {
    Remove-PSSession $session
}
