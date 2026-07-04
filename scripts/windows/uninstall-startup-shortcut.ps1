$ErrorActionPreference = "Stop"

$StartupDir = [Environment]::GetFolderPath("Startup")
$ShortcutPath = Join-Path $StartupDir "FastWispr.lnk"

if (Test-Path $ShortcutPath) {
    Remove-Item -Force $ShortcutPath
    Write-Host "Removed startup shortcut: $ShortcutPath" -ForegroundColor Green
}
else {
    Write-Host "Startup shortcut not found: $ShortcutPath" -ForegroundColor Yellow
}
