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

$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (!(Test-Path $Python)) {
    throw "Windows venv missing at $Python. Run .\scripts\windows\setup.ps1 first."
}

if (-not $SkipTests) {
    Invoke-External "Running tests before build." { & $Python -m pytest -q }
    Invoke-External "Running Windows smoke before build." { & $Python -m fastwispr.cli windows-smoke }
}

Invoke-External "Building FastWispr with PyInstaller." {
    & $Python -m PyInstaller `
        --noconfirm `
        --clean `
        --name FastWispr `
        --onedir `
        --paths (Join-Path $RepoRoot "src") `
        --hidden-import fastwispr.windows.tray `
        --hidden-import fastwispr.windows.settings_ui `
        --hidden-import fastwispr.windows.audio `
        --hidden-import fastwispr.windows.hotkeys `
        --hidden-import fastwispr.windows.hold_to_talk `
        --hidden-import fastwispr.windows.injector `
        --hidden-import fastwispr.windows.mouse_buttons `
        --hidden-import fastwispr.windows.overlay `
        --hidden-import fastwispr.windows.sounds `
        --hidden-import keyboard `
        --hidden-import sounddevice `
        --hidden-import pyautogui `
        --hidden-import pyperclip `
        (Join-Path $RepoRoot "src\fastwispr\__main__.py")
}

$Exe = Join-Path $RepoRoot "dist\FastWispr\FastWispr.exe"
if (!(Test-Path $Exe)) {
    throw "PyInstaller did not produce $Exe"
}

Invoke-External "Verifying packaged executable." { & $Exe windows-smoke }

Write-Host "Built: $Exe" -ForegroundColor Green
