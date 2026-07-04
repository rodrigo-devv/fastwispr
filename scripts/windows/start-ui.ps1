param(
    [string]$Hotkey = "ctrl+space",
    [string]$HoldButton = "xbutton1",
    [ValidateSet("keyboard", "mouse")]
    [string]$Trigger = "keyboard",
    [ValidateSet("hold", "toggle")]
    [string]$ActivationMode = "toggle",
    [string]$Language = "pt-en",
    [double]$MinRecordSeconds = 0.35,
    [double]$MinAudioRms = 0.003
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)
Set-Location $RepoRoot

$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (!(Test-Path $Python)) {
    throw "Windows venv missing at $Python. Run the project setup/update step before starting FastWispr."
}

$ConfigDir = Join-Path $env:APPDATA "FastWispr"
$ConfigFile = Join-Path $ConfigDir "config.toml"
New-Item -ItemType Directory -Force $ConfigDir | Out-Null

& $Python -m fastwispr.cli --config $ConfigFile config set hotkeys.dictate_toggle $Hotkey | Out-Null
& $Python -m fastwispr.cli --config $ConfigFile config set hotkeys.hold_button $HoldButton | Out-Null
& $Python -m fastwispr.cli --config $ConfigFile config set activation.trigger $Trigger | Out-Null
& $Python -m fastwispr.cli --config $ConfigFile config set activation.mode $ActivationMode | Out-Null
& $Python -m fastwispr.cli --config $ConfigFile config set stt.language $Language | Out-Null
& $Python -m fastwispr.cli --config $ConfigFile config set dictation.min_record_seconds $MinRecordSeconds | Out-Null
& $Python -m fastwispr.cli --config $ConfigFile config set dictation.min_audio_rms $MinAudioRms | Out-Null

Write-Host "Starting FastWispr tray." -ForegroundColor Green
if ($Trigger -eq "keyboard") {
    Write-Host "Press $Hotkey to start. Press again to stop/transcribe/paste." -ForegroundColor Yellow
}
elseif ($ActivationMode -eq "toggle") {
    Write-Host "Press $HoldButton to start. Press again to stop/transcribe/paste." -ForegroundColor Yellow
}
else {
    Write-Host "Hold $HoldButton to record. Release to transcribe and paste." -ForegroundColor Yellow
}
Write-Host "Language mode: $Language (default pt-en auto-detects EN/PT; use -Language pt-BR or -Language en to force one language)" -ForegroundColor Yellow
Write-Host "Dictation guard: min $MinRecordSeconds sec, min RMS $MinAudioRms" -ForegroundColor Yellow
Write-Host "Config: $ConfigFile"

& $Python -m fastwispr.cli --config $ConfigFile run-windows-tray
