param([switch]$Files, [switch]$Mcp)
$ErrorActionPreference = 'Stop'
$sfxSessionPath = Join-Path $PSScriptRoot 'local-install\claude-session.json'
$sfxState = if (Test-Path -LiteralPath $sfxSessionPath) { (Get-Content -LiteralPath $sfxSessionPath -Raw | ConvertFrom-Json).state } else { Join-Path $env:LOCALAPPDATA 'SoundPilotLearning' }
$sfxPython = Join-Path $PSScriptRoot 'runtime\env\Scripts\python.exe'
$env:PATH = "$(Join-Path $PSScriptRoot 'runtime\tools');$env:PATH"
$sfxArgs = @((Join-Path $PSScriptRoot 'migration\health_check.py'), '--state', $sfxState)
if ($Files) { $sfxArgs += '--verify-files' }
if ($Mcp) { $sfxArgs += '--mcp' }
& $sfxPython @sfxArgs
exit $LASTEXITCODE
