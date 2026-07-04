param(
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"

function Invoke-External {
    param(
        [string]$Description,
        [scriptblock]$Command
    )
    Write-Host $Description -ForegroundColor Yellow
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE"
    }
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)
Set-Location $RepoRoot

$VenvDir = Join-Path $RepoRoot ".venv"
$Python = Join-Path $VenvDir "Scripts\python.exe"

if (!(Test-Path $Python)) {
    Write-Host "Creating Windows virtualenv at $VenvDir" -ForegroundColor Yellow
    $PyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($PyLauncher) {
        & py -3.11 -m venv $VenvDir
    }
    else {
        & python -m venv $VenvDir
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Virtualenv creation failed with exit code $LASTEXITCODE"
    }
}

if (!(Test-Path $Python)) {
    throw "Python executable not found after venv setup: $Python"
}

Invoke-External "Upgrading packaging tools." { & $Python -m pip install --upgrade pip setuptools wheel }
Invoke-External "Installing FastWispr development extras." { & $Python -m pip install -e ".[windows,stt,test,packaging]" }

if (-not $SkipTests) {
    Invoke-External "Running tests." { & $Python -m pytest -q }
    Invoke-External "Running Windows smoke." { & $Python -m fastwispr.cli windows-smoke }
}

Write-Host "FastWispr setup/update complete." -ForegroundColor Green
Write-Host "Launch with: powershell -ExecutionPolicy Bypass -File .\scripts\windows\start-ui.ps1" -ForegroundColor Cyan
