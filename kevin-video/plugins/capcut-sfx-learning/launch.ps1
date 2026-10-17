param([switch]$Http, [int]$Port = 8776)
$ErrorActionPreference = 'Stop'
$sfxState = if ($env:SOUNDPILOT_STATE) { $env:SOUNDPILOT_STATE } else { Join-Path $env:LOCALAPPDATA 'SoundPilotLearning' }
$sfxRuntimeFile = Join-Path $sfxState 'runtime.json'
$sfxPython = if (Test-Path -LiteralPath $sfxRuntimeFile) { (Get-Content -LiteralPath $sfxRuntimeFile -Raw | ConvertFrom-Json).python } else { Join-Path $PSScriptRoot '.venv\Scripts\python.exe' }
if (-not (Test-Path -LiteralPath $sfxPython)) { throw 'Run setup.py first. See INSTALL.md.' }
$sfxArgs = @((Join-Path $PSScriptRoot 'server.py'))
if ($Http) { $sfxArgs += @('--http', '--port', "$Port") }
& $sfxPython @sfxArgs
exit $LASTEXITCODE
