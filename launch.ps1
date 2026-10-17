param([switch]$Http, [int]$Port = 8776)
$ErrorActionPreference = 'Stop'
$sfxSession = Join-Path $PSScriptRoot '..\..\local-install\claude-session.json'
if (-not $env:SOUNDPILOT_STATE -and (Test-Path -LiteralPath $sfxSession)) {
    $env:SOUNDPILOT_STATE = (Get-Content -LiteralPath $sfxSession -Raw | ConvertFrom-Json).state
}
$sfxState = if ($env:SOUNDPILOT_STATE) { $env:SOUNDPILOT_STATE } else { Join-Path $env:LOCALAPPDATA 'SoundPilotLearning' }
$sfxRuntimeFile = Join-Path $sfxState 'runtime.json'
if (-not (Test-Path -LiteralPath $sfxRuntimeFile)) { throw 'Run INSTALL_CLAUDE_CODE.bat first; read README_BN.md.' }
$sfxRuntime = Get-Content -LiteralPath $sfxRuntimeFile -Raw | ConvertFrom-Json
if ($sfxRuntime.ffmpeg_bin) { $env:PATH = "$($sfxRuntime.ffmpeg_bin);$env:PATH" }
$sfxPython = $sfxRuntime.python
if (-not (Test-Path -LiteralPath $sfxPython)) { throw 'Configured Python moved. Rerun the bundle installer.' }
$sfxArgs = @((Join-Path $PSScriptRoot 'server.py'))
if ($Http) { $sfxArgs += @('--http', '--port', "$Port") }
& $sfxPython @sfxArgs
exit $LASTEXITCODE
