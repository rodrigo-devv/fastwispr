param(
    [int]$Port = 8765
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)
Set-Location $RepoRoot

$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (!(Test-Path $Python)) {
    throw "Windows venv missing at $Python. Run the project setup/update step before starting the dev runner."
}

$TokenDir = Join-Path $env:USERPROFILE ".fastwispr"
$TokenFile = Join-Path $TokenDir "dev-runner-token"

Write-Host "Starting FastWispr dev runner in the interactive Windows session." -ForegroundColor Green
Write-Host "Host: 127.0.0.1"
Write-Host "Port: $Port"
Write-Host "Token file: $TokenFile"
Write-Host "Leave this window open while Friday runs GUI/audio tests." -ForegroundColor Yellow

& $Python -m fastwispr.dev_runner --host 127.0.0.1 --port $Port --token-file $TokenFile
