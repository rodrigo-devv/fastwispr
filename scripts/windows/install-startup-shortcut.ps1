param(
    [string]$RepoRoot = "C:\development\fastwispr"
)

$ErrorActionPreference = "Stop"

$StartupDir = [Environment]::GetFolderPath("Startup")
$ShortcutPath = Join-Path $StartupDir "FastWispr.lnk"
$AppExe = Join-Path $RepoRoot "dist\FastWispr\FastWispr.exe"

if (!(Test-Path $AppExe)) {
    throw "FastWispr executable not found: $AppExe. Run scripts\windows\build.ps1 first."
}

$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $AppExe
$Shortcut.Arguments = ""
$Shortcut.WorkingDirectory = Split-Path -Parent $AppExe
$Shortcut.IconLocation = "$AppExe,0"
$Shortcut.Description = "FastWispr dictation startup"
$Shortcut.Save()

Write-Host "Installed startup shortcut: $ShortcutPath" -ForegroundColor Green
Write-Host "Shortcut target: $AppExe" -ForegroundColor Yellow
