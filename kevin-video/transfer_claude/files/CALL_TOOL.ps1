param([Parameter(Mandatory=$true)][string]$Tool, [string]$InputFile = '')
$ErrorActionPreference = 'Stop'
$sfxSession = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'local-install\claude-session.json') -Raw | ConvertFrom-Json
$env:SOUNDPILOT_STATE = $sfxSession.state
$sfxRuntime = Get-Content -LiteralPath (Join-Path $sfxSession.state 'runtime.json') -Raw | ConvertFrom-Json
if ($sfxRuntime.ffmpeg_bin) { $env:PATH = "$($sfxRuntime.ffmpeg_bin);$env:PATH" }
$sfxArgs = @((Join-Path $PSScriptRoot 'plugins\capcut-sfx-learning\cli.py'), $Tool)
if ($InputFile) { $sfxArgs += @('--input', [IO.Path]::GetFullPath($InputFile)) }
& $sfxRuntime.python @sfxArgs
exit $LASTEXITCODE
