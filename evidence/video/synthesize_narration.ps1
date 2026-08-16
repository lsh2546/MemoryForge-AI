param(
    [string]$InputPath = "$PSScriptRoot\narration.txt",
    [string]$OutputPath = "$PSScriptRoot\audio\memoryforge-narration.wav"
)

New-Item -ItemType Directory -Force -Path (Split-Path $OutputPath) | Out-Null
Add-Type -AssemblyName System.Speech
$voice = [System.Speech.Synthesis.SpeechSynthesizer]::new()
$voice.Rate = 2
$voice.Volume = 100
$voice.SetOutputToWaveFile($OutputPath)
$voice.Speak((Get-Content -Raw -LiteralPath $InputPath))
$voice.Dispose()
