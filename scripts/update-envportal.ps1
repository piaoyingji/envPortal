param(
    [string]$RepoUrl = "https://github.com/piaoyingji/envPortal.git",
    [string]$Branch = "main",
    [string]$InstallDir = "C:\EnvPortal"
)

$ErrorActionPreference = "Stop"

function Require-Command($Name, $InstallHint) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name is required. $InstallHint"
    }
}

Require-Command git "Install Git for Windows, then rerun this script."

if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
}

if (-not (Test-Path (Join-Path $InstallDir ".git"))) {
    $parent = Split-Path -Parent $InstallDir
    if ($parent -and -not (Test-Path $parent)) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }
    if ((Get-ChildItem -LiteralPath $InstallDir -Force | Select-Object -First 1)) {
        throw "InstallDir exists but is not a Git repository and is not empty: $InstallDir"
    }
    git clone --branch $Branch $RepoUrl $InstallDir
} else {
    git -C $InstallDir fetch origin $Branch
    git -C $InstallDir checkout $Branch
    git -C $InstallDir pull --ff-only origin $Branch
}

$python = Get-Command py -ErrorAction SilentlyContinue
if ($python) {
    & py -3 -m pip install -r (Join-Path $InstallDir "requirements.txt")
} else {
    Require-Command python "Install Python 3, then rerun this script."
    & python -m pip install -r (Join-Path $InstallDir "requirements.txt")
}

Write-Host "EnvPortal updated at $InstallDir"
