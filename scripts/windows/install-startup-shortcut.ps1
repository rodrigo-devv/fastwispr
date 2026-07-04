param(
    [string]$RepoRoot = "C:\development\fastwispr",
    [string]$Hotkey = "ctrl+space",
    [string]$Language = "pt-en",
    [ValidateSet("keyboard", "mouse")]
    [string]$Trigger = "keyboard",
    [ValidateSet("hold", "toggle")]
    [string]$ActivationMode = "toggle",
    [double]$MinRecordSeconds = 0.35,
    [double]$MinAudioRms = 0.003
)

$ErrorActionPreference = "Stop"

$StartupDir = [Environment]::GetFolderPath("Startup")
$ShortcutPath = Join-Path $StartupDir "FastWispr.lnk"
$Launcher = Join-Path $RepoRoot "scripts\windows\start-ui.ps1"
if (!(Test-Path $Launcher)) {
    throw "Launcher not found: $Launcher"
}

$PowerShell = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Minimized -File `"$Launcher`" -Hotkey $Hotkey -Language $Language -Trigger $Trigger -ActivationMode $ActivationMode -MinRecordSeconds $MinRecordSeconds -MinAudioRms $MinAudioRms"

$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $PowerShell
$Shortcut.Arguments = $Arguments
$Shortcut.WorkingDirectory = $RepoRoot
$Shortcut.IconLocation = "$PowerShell,0"
$Shortcut.Description = "FastWispr dictation startup"
$Shortcut.Save()

Write-Host "Installed startup shortcut: $ShortcutPath" -ForegroundColor Green
Write-Host "Shortcut args: $Arguments" -ForegroundColor Yellow
