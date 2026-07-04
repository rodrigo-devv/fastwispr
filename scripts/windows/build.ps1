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

function Invoke-PyInstallerBuild {
    param(
        [string]$Name,
        [switch]$Windowed
    )

    $CollectDataArgs = @(
        "--collect-data", "faster_whisper"
    )

    $HiddenImportArgs = @(
        "--hidden-import", "fastwispr.windows.tray",
        "--hidden-import", "fastwispr.windows.settings_ui",
        "--hidden-import", "fastwispr.windows.audio",
        "--hidden-import", "fastwispr.windows.hotkeys",
        "--hidden-import", "fastwispr.windows.hold_to_talk",
        "--hidden-import", "fastwispr.windows.injector",
        "--hidden-import", "fastwispr.windows.mouse_buttons",
        "--hidden-import", "fastwispr.windows.overlay",
        "--hidden-import", "fastwispr.windows.sounds",
        "--hidden-import", "winsound",
        "--hidden-import", "keyboard",
        "--hidden-import", "sounddevice",
        "--hidden-import", "pyautogui",
        "--hidden-import", "pyperclip"
    )

    $Args = @(
        "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name", $Name,
        "--onedir",
        "--paths", (Join-Path $RepoRoot "src")
    )
    if ($Windowed) {
        $Args += "--windowed"
    }
    $Args += $CollectDataArgs
    $Args += $HiddenImportArgs
    $Args += (Join-Path $RepoRoot "src\fastwispr\__main__.py")

    & $Python @Args
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)
Set-Location $RepoRoot

Get-Process "FastWispr", "FastWisprCli" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500
$BuildDir = Join-Path $RepoRoot "build"
Remove-Item -Recurse -Force $BuildDir -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force (Join-Path $RepoRoot "dist\FastWispr") -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force (Join-Path $RepoRoot "dist\FastWisprCli") -ErrorAction SilentlyContinue

$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (!(Test-Path $Python)) {
    throw "Windows venv missing at $Python. Run .\scripts\windows\setup.ps1 first."
}

if (-not $SkipTests) {
    Invoke-External "Running tests before build." { & $Python -m pytest -q }
    Invoke-External "Running Windows smoke before build." { & $Python -m fastwispr.cli windows-smoke }
}

Invoke-External "Building FastWispr windowed app with PyInstaller." { Invoke-PyInstallerBuild -Name "FastWispr" -Windowed }
Invoke-External "Building FastWisprCli diagnostic console with PyInstaller." { Invoke-PyInstallerBuild -Name "FastWisprCli" }

$AppExe = Join-Path $RepoRoot "dist\FastWispr\FastWispr.exe"
$CliExe = Join-Path $RepoRoot "dist\FastWisprCli\FastWisprCli.exe"
if (!(Test-Path $AppExe)) {
    throw "PyInstaller did not produce $AppExe"
}
if (!(Test-Path $CliExe)) {
    throw "PyInstaller did not produce $CliExe"
}

$SileroVadRelativePath = "_internal\faster_whisper\assets\silero_vad_v6.onnx"
$AppSileroVad = Join-Path (Split-Path -Parent $AppExe) $SileroVadRelativePath
$CliSileroVad = Join-Path (Split-Path -Parent $CliExe) $SileroVadRelativePath
if (!(Test-Path $AppSileroVad)) {
    throw "Missing packaged faster-whisper VAD asset: $AppSileroVad"
}
if (!(Test-Path $CliSileroVad)) {
    throw "Missing packaged faster-whisper VAD asset: $CliSileroVad"
}

Invoke-External "Verifying packaged CLI executable." { & $CliExe windows-smoke }
Invoke-External "Verifying packaged CLI sounds." { & $CliExe sound-smoke }

Write-Host "Verifying packaged windowed app executable." -ForegroundColor Yellow
$AppSmoke = Start-Process -FilePath $AppExe -ArgumentList "windows-smoke" -Wait -PassThru
if ($AppSmoke.ExitCode -ne 0) {
    throw "Verifying packaged windowed app executable failed with exit code $($AppSmoke.ExitCode)"
}

$BuildDir = Join-Path $RepoRoot "build"
Remove-Item -Recurse -Force $BuildDir -ErrorAction SilentlyContinue
Remove-Item -Force (Join-Path $RepoRoot "FastWispr.spec") -ErrorAction SilentlyContinue
Remove-Item -Force (Join-Path $RepoRoot "FastWisprCli.spec") -ErrorAction SilentlyContinue

Write-Host "Built app: $AppExe" -ForegroundColor Green
Write-Host "Built CLI: $CliExe" -ForegroundColor Green
