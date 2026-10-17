[CmdletBinding()]
param([string]$StateRoot = '', [string]$DraftRoot = '', [switch]$UsePortable,
      [switch]$NoRegister, [switch]$ReplaceClaudeRegistration)
$ErrorActionPreference = 'Stop'
$sfxBundle = $PSScriptRoot
$sfxPlugin = Join-Path $sfxBundle 'plugins\capcut-sfx-learning'
$sfxBase = Join-Path $sfxBundle 'runtime\python'
$sfxEnv = Join-Path $sfxBundle 'runtime\env'
$sfxPython = Join-Path $sfxEnv 'Scripts\python.exe'
$sfxTools = Join-Path $sfxBundle 'runtime\tools'
if (-not $StateRoot) { $StateRoot = Join-Path $env:LOCALAPPDATA 'SoundPilotLearning' }
$StateRoot = [IO.Path]::GetFullPath($StateRoot)
$env:SOUNDPILOT_STATE = $StateRoot
$env:PATH = "$sfxTools;$env:PATH"
$env:CT2_FORCE_CPU_ISA = 'GENERIC'
$env:CT2_USE_MKL = '0'
# Python's venv launcher reads this file; no pip console launcher is used.
$sfxCfg = "home = $sfxBase`r`ninclude-system-site-packages = false`r`nversion = 3.12.14`r`nexecutable = $(Join-Path $sfxBase 'python.exe')`r`n"
[IO.File]::WriteAllText((Join-Path $sfxEnv 'pyvenv.cfg'), $sfxCfg, [Text.UTF8Encoding]::new($false))
function Invoke-SfxPython([string[]]$Arguments) {
    & $sfxPython @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Bundle operation failed (exit $LASTEXITCODE)." }
}
$sfxConfigPath = Join-Path $StateRoot 'config.json'
$sfxRuntimePath = Join-Path $StateRoot 'runtime.json'
$sfxReuse = $false
if (-not $UsePortable -and (Test-Path -LiteralPath $sfxConfigPath) -and (Test-Path -LiteralPath $sfxRuntimePath)) {
    $sfxExistingConfig = Get-Content -LiteralPath $sfxConfigPath -Raw | ConvertFrom-Json
    $sfxExistingRuntime = Get-Content -LiteralPath $sfxRuntimePath -Raw | ConvertFrom-Json
    $sfxReuse = (Test-Path -LiteralPath $sfxExistingRuntime.python) -and (Test-Path -LiteralPath $sfxExistingConfig.library) -and (Test-Path -LiteralPath $sfxExistingConfig.model_root) -and (Test-Path -LiteralPath $sfxExistingConfig.draft_root) -and (Test-Path -LiteralPath (Join-Path $StateRoot 'memory.json')) -and (Test-Path -LiteralPath (Join-Path $StateRoot 'data\zoom_style.json')) -and (Test-Path -LiteralPath (Join-Path $StateRoot 'data\hook_style.json'))
    if ($DraftRoot -and [IO.Path]::GetFullPath($DraftRoot) -ne [IO.Path]::GetFullPath($sfxExistingConfig.draft_root)) { $sfxReuse = $false }
}
if ($sfxReuse) {
    Write-Host 'Sharing the current Codex state/runtime. Newer learning remains active.'
} else {
    if (-not $DraftRoot) { $DraftRoot = Join-Path $env:LOCALAPPDATA 'CapCut\User Data\Projects\com.lveditor.draft' }
    if (-not (Test-Path -LiteralPath $DraftRoot)) {
        $sfxDefault = Join-Path $env:LOCALAPPDATA 'CapCut\User Data\Projects\com.lveditor.draft'
        if ([IO.Path]::GetFullPath($DraftRoot) -ne [IO.Path]::GetFullPath($sfxDefault)) { throw 'The specified -DraftRoot must exist.' }
        New-Item -ItemType Directory -Path $DraftRoot -Force | Out-Null
    }
    Invoke-SfxPython @((Join-Path $sfxBundle 'migration\restore_state.py'), '--state', $StateRoot, '--draft-root', [IO.Path]::GetFullPath($DraftRoot))
    $sfxRuntime = @{ python = $sfxPython; ffmpeg_bin = $sfxTools } | ConvertTo-Json
    [IO.File]::WriteAllText($sfxRuntimePath, $sfxRuntime, [Text.UTF8Encoding]::new($false))
    Invoke-SfxPython @((Join-Path $sfxPlugin 'cli.py'), 'configure', '--input', (Join-Path $StateRoot 'migration-config-input.json'))
}
New-Item -ItemType Directory -Path (Join-Path $sfxBundle 'local-install') -Force | Out-Null
$sfxSession = @{ state = $StateRoot; shared_existing_runtime = $sfxReuse } | ConvertTo-Json
[IO.File]::WriteAllText((Join-Path $sfxBundle 'local-install\claude-session.json'), $sfxSession, [Text.UTF8Encoding]::new($false))
Invoke-SfxPython @((Join-Path $sfxBundle 'migration\health_check.py'), '--state', $StateRoot)
if (-not $NoRegister) {
    $sfxClaude = Get-Command claude -ErrorAction SilentlyContinue
    if (-not $sfxClaude) { throw 'Runtime/memory ready. Install/sign in to native Windows Claude Code, then rerun this installer. See docs/SETUP.md.' }
    $sfxSkillSource = Join-Path $sfxPlugin 'skills\capcut-sfx-learning'
    $sfxSkillTarget = Join-Path $env:USERPROFILE '.claude\skills\capcut-sfx-learning'
    if (Test-Path -LiteralPath $sfxSkillTarget) {
        $sfxBackup = Join-Path $env:USERPROFILE ('.claude\migration-backups\capcut-sfx-learning-' + [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-fff'))
        New-Item -ItemType Directory -Path (Split-Path $sfxBackup -Parent) -Force | Out-Null
        Copy-Item -LiteralPath $sfxSkillTarget -Destination $sfxBackup -Recurse
    }
    New-Item -ItemType Directory -Path $sfxSkillTarget -Force | Out-Null
    Get-ChildItem -LiteralPath $sfxSkillSource -Force | ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination $sfxSkillTarget -Recurse -Force }
    if ($ReplaceClaudeRegistration) {
        & $sfxClaude.Source mcp remove --scope user capcut-sfx-learning
        if ($LASTEXITCODE -ne 0) { throw 'Could not remove the requested old Claude registration. Other servers remain unchanged.' }
    }
    & $sfxClaude.Source mcp add --scope user --transport stdio capcut-sfx-learning -- powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $sfxPlugin 'launch.ps1')
    if ($LASTEXITCODE -ne 0) { throw 'MCP registration failed. If the same name already exists, use -ReplaceClaudeRegistration after reviewing claude mcp get capcut-sfx-learning.' }
    & $sfxClaude.Source mcp get capcut-sfx-learning
    if ($LASTEXITCODE -ne 0) { throw 'Claude could not read the MCP registration.' }
}
Write-Host "Ready. State: $StateRoot"
Write-Host 'Start a fresh Claude Code session. Run /mcp, /capcut-sfx-learning, then a saved-project list.'
