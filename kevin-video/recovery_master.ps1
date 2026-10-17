[CmdletBinding()]
param(
    [ValidateSet('menu','install','check','usage','memory','projects','prepare','status','apply','learn','zoom-prepare','zoom-apply','zoom-learn','http','restore-sounds')]
    [string]$Mode = 'menu',
    [string]$StateRoot = '', [string]$DraftRoot = '', [string]$LibraryRoot = '',
    [switch]$NoRegister, [switch]$ForceMemory, [switch]$VerifyFiles,
    [string]$InputFile = '', [string]$BatchId = '', [string]$JobId = '',
    [string]$Project = '', [string]$Timeline = ''
)
$ErrorActionPreference = 'Stop'
$sfxBundle = $PSScriptRoot
$sfxPlugin = Join-Path $sfxBundle 'plugins\capcut-sfx-learning'
$sfxBase = Join-Path $sfxBundle 'runtime\python'
$sfxEnv = Join-Path $sfxBundle 'runtime\env'
$sfxPython = Join-Path $sfxEnv 'Scripts\python.exe'
$sfxTools = Join-Path $sfxBundle 'runtime\tools'
if (-not $StateRoot) { $StateRoot = Join-Path $env:LOCALAPPDATA 'SoundPilotLearning' }
if (-not $DraftRoot) { $DraftRoot = Join-Path $env:LOCALAPPDATA 'CapCut\User Data\Projects\com.lveditor.draft' }
if (-not $LibraryRoot) { $LibraryRoot = Join-Path $sfxPlugin 'library' }
$env:SOUNDPILOT_STATE = [IO.Path]::GetFullPath($StateRoot)
$env:PATH = "$sfxTools;$env:PATH"
$env:CT2_FORCE_CPU_ISA = 'GENERIC'
$env:CT2_USE_MKL = '0'
$sfxCfg = "home = $sfxBase`r`ninclude-system-site-packages = false`r`nversion = 3.12.14`r`nexecutable = $(Join-Path $sfxBase 'python.exe')`r`n"
[IO.File]::WriteAllText((Join-Path $sfxEnv 'pyvenv.cfg'), $sfxCfg, [Text.UTF8Encoding]::new($false))

function Invoke-SfxPython {
    param([string[]]$Arguments)
    & $sfxPython @Arguments
    if ($LASTEXITCODE -ne 0) { throw "SoundPilot operation failed (exit $LASTEXITCODE). No automatic bypass was used." }
}
function Find-SfxCodex {
    $sfxCommand = Get-Command codex -ErrorAction SilentlyContinue
    if ($sfxCommand) { return $sfxCommand.Source }
    $sfxBin = Join-Path $env:LOCALAPPDATA 'OpenAI\Codex\bin'
    if (Test-Path -LiteralPath $sfxBin) {
        $sfxFound = Get-ChildItem -LiteralPath $sfxBin -Filter 'codex.exe' -Recurse -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($sfxFound) { return $sfxFound.FullName }
    }
    return $null
}
function Install-SfxRecovery {
    New-Item -ItemType Directory -Path $env:SOUNDPILOT_STATE -Force | Out-Null
    if (-not (Test-Path -LiteralPath $DraftRoot)) {
        $sfxDefaultDraft = Join-Path $env:LOCALAPPDATA 'CapCut\User Data\Projects\com.lveditor.draft'
        if ([IO.Path]::GetFullPath($DraftRoot) -ne [IO.Path]::GetFullPath($sfxDefaultDraft)) { throw 'Choose an existing CapCut draft directory with -DraftRoot.' }
        New-Item -ItemType Directory -Path $DraftRoot -Force | Out-Null
    }
    $sfxRestore = @('--state', $env:SOUNDPILOT_STATE, '--library', [IO.Path]::GetFullPath($LibraryRoot))
    if ($ForceMemory) { $sfxRestore += '--force-memory' }
    Invoke-SfxPython -Arguments (@((Join-Path $sfxBundle 'restore_memory.py')) + $sfxRestore)
    $sfxRuntime = @{ python = $sfxPython; ffmpeg_bin = $sfxTools }
    $sfxRuntime | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $env:SOUNDPILOT_STATE 'runtime.json') -Encoding UTF8
    $sfxParameters = @{ draft_root = [IO.Path]::GetFullPath($DraftRoot); library = [IO.Path]::GetFullPath($LibraryRoot); model_root = (Join-Path $sfxBundle 'models') } | ConvertTo-Json -Compress
    $sfxParameterFile = Join-Path $env:SOUNDPILOT_STATE 'restore-config-input.json'
    [IO.File]::WriteAllText($sfxParameterFile, $sfxParameters, [Text.UTF8Encoding]::new($false))
    Invoke-SfxPython -Arguments @((Join-Path $sfxPlugin 'cli.py'), 'configure', '--input', $sfxParameterFile)
    if (-not $NoRegister) {
        $sfxCodex = Find-SfxCodex
        if ($sfxCodex) {
            $sfxExisting = & $sfxCodex plugin list --json | ConvertFrom-Json
            foreach ($sfxItem in @($sfxExisting.installed)) {
                if ($sfxItem.name -eq 'capcut-sfx-learning' -and $sfxItem.marketplaceName -in @('srijon-sfx', 'srijon-sfx-recovery')) {
                    & $sfxCodex plugin remove $sfxItem.pluginId
                    if ($LASTEXITCODE -ne 0) { throw 'Close active SFX MCP sessions, then retry the owned-plugin registration.' }
                }
            }
            $sfxMarkets = & $sfxCodex plugin marketplace list --json | ConvertFrom-Json
            if (@($sfxMarkets.marketplaces | Where-Object { $_.name -eq 'srijon-sfx-recovery' }).Count -gt 0) {
                & $sfxCodex plugin marketplace remove 'srijon-sfx-recovery'
                if ($LASTEXITCODE -ne 0) { throw 'Could not refresh the recovery marketplace registration.' }
            }
            & $sfxCodex plugin marketplace add $sfxBundle --json
            if ($LASTEXITCODE -ne 0) { throw 'Recovery marketplace registration failed.' }
            & $sfxCodex plugin add 'capcut-sfx-learning@srijon-sfx-recovery' --json
            if ($LASTEXITCODE -ne 0) { throw 'Recovery plugin registration failed.' }
            Write-Host 'Codex plugin restored. Open a new Codex chat to load it.'
        } else { Write-Host 'Runtime/memory restored. Install/sign in to Codex, then run MASTER.bat install again to register tools.' }
    }
    Invoke-SfxPython -Arguments @((Join-Path $sfxBundle 'health_check.py'), '--state', $env:SOUNDPILOT_STATE)
    Write-Host "Sound library: $LibraryRoot"
    Write-Host "State/memory: $env:SOUNDPILOT_STATE"
}
function Restore-SfxSounds {
    $sfxTarget = if ($LibraryRoot -ne (Join-Path $sfxPlugin 'library')) { $LibraryRoot } else { Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Sound Effect Sidebar Library' }
    Invoke-SfxPython -Arguments @((Join-Path $sfxBundle 'restore_memory.py'), '--copy-sounds-to', $sfxTarget)
}
function Invoke-SfxMode {
    param([string]$Action)
    switch ($Action) {
        'install' { Install-SfxRecovery }
        'check' {
            $sfxHealthArgs = @((Join-Path $sfxBundle 'health_check.py'), '--state', $env:SOUNDPILOT_STATE)
            if ($VerifyFiles) { $sfxHealthArgs += '--verify-files' }
            Invoke-SfxPython -Arguments $sfxHealthArgs
        }
        'usage' { Get-Content -LiteralPath (Join-Path $sfxBundle 'USAGE.txt'); Write-Host "`nFull adoption notes: $(Join-Path $sfxBundle 'reports')" }
        'memory' { Invoke-SfxPython -Arguments @((Join-Path $sfxBundle 'health_check.py'), '--state', $env:SOUNDPILOT_STATE, '--memory-only') }
        'projects' { Invoke-SfxPython -Arguments @((Join-Path $sfxPlugin 'cli.py'), 'list_projects') }
        'prepare' {
            if (-not $InputFile) { $script:InputFile = Read-Host 'Path to targets JSON (see examples\prepare.json)' }
            Invoke-SfxPython -Arguments @((Join-Path $sfxPlugin 'cli.py'), 'prepare_batch', '--input', $InputFile)
            Write-Host 'Give the returned batch ID to Codex. SFX + contextual zooms are the default; footage is analyzed once.'
        }
        'status' {
            if (-not $BatchId) { $script:BatchId = Read-Host 'Batch ID' }
            $sfxArguments = @{ batch_id = $BatchId } | ConvertTo-Json -Compress
            Invoke-SfxPython -Arguments @((Join-Path $sfxPlugin 'cli.py'), 'batch_status', '--json', $sfxArguments)
        }
        'apply' {
            if (-not $BatchId) { $script:BatchId = Read-Host 'Authorized staged/audited batch ID (CapCut must be closed)' }
            $sfxArguments = @{ batch_id = $BatchId } | ConvertTo-Json -Compress
            Invoke-SfxPython -Arguments @((Join-Path $sfxPlugin 'cli.py'), 'preflight_batch', '--json', $sfxArguments)
            Invoke-SfxPython -Arguments @((Join-Path $sfxPlugin 'cli.py'), 'apply_batch', '--json', $sfxArguments)
        }
        'learn' {
            if (-not $InputFile) { $script:InputFile = Read-Host 'Revision JSON path (see examples\learn.json)' }
            Invoke-SfxPython -Arguments @((Join-Path $sfxPlugin 'cli.py'), 'learn_revision', '--input', $InputFile)
        }
        'zoom-prepare' {
            if (-not $InputFile) { $script:InputFile = Read-Host 'Cached-analysis zoom targets JSON path' }
            Invoke-SfxPython -Arguments @((Join-Path $sfxPlugin 'cli.py'), 'prepare_zoom_batch', '--input', $InputFile)
        }
        'zoom-apply' {
            if (-not $BatchId) { $script:BatchId = Read-Host 'Authorized framing-reviewed zoom batch ID (CapCut closed)' }
            $sfxArguments = @{ batch_id = $BatchId } | ConvertTo-Json -Compress
            Invoke-SfxPython -Arguments @((Join-Path $sfxPlugin 'cli.py'), 'apply_zoom_batch', '--json', $sfxArguments)
        }
        'zoom-learn' {
            if (-not $JobId) { $script:JobId = Read-Host 'Applied zoom job ID' }
            $sfxArguments = @{ job_id = $JobId } | ConvertTo-Json -Compress
            Invoke-SfxPython -Arguments @((Join-Path $sfxPlugin 'cli.py'), 'learn_zoom_revision', '--json', $sfxArguments)
        }
        'http' { Invoke-SfxPython -Arguments @((Join-Path $sfxPlugin 'server.py'), '--http') }
        'restore-sounds' { Restore-SfxSounds }
    }
}
if ($Mode -ne 'menu') { Invoke-SfxMode -Action $Mode; exit 0 }
while ($true) {
    Write-Host "`n=== SoundPilot complete recovery ==="
    Write-Host '1 Install/restore memory + runtime + Codex plugin'
    Write-Host '2 Verify runtime, models, sounds and memory'
    Write-Host '3 Usage / instructions'
    Write-Host '4 Learned memory summary'
    Write-Host '5 List saved CapCut projects'
    Write-Host '6 Prepare 1-5 videos for SFX + zoom from targets JSON'
    Write-Host '7 Check batch status'
    Write-Host '8 Apply an authorized staged/audited batch'
    Write-Host '9 Learn a saved manual revision from JSON'
    Write-Host 'S Restore missing sounds to Documents/Sidebar library'
    Write-Host 'H Start loopback MCP HTTP for a supported secure tunnel'
    Write-Host '0 Exit'
    $sfxChoice = Read-Host 'Choose'
    if ($sfxChoice -eq '0') { break }
    $sfxModes = @{ '1'='install'; '2'='check'; '3'='usage'; '4'='memory'; '5'='projects'; '6'='prepare'; '7'='status'; '8'='apply'; '9'='learn'; 'S'='restore-sounds'; 'H'='http' }
    if ($sfxModes.ContainsKey($sfxChoice.ToUpperInvariant())) {
        try { Invoke-SfxMode -Action $sfxModes[$sfxChoice.ToUpperInvariant()] } catch { Write-Host $_.Exception.Message -ForegroundColor Red }
    }
}
