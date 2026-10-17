$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$taskPython = 'C:\Users\srijon\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) { & $taskPython -m venv .venv }
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& '.\.venv\Scripts\python.exe' -X utf8 -c "from fastembed import TextEmbedding; m=TextEmbedding(model_name='BAAI/bge-small-en-v1.5',cache_dir='models',threads=2); print(next(m.embed(['Sound effect'])).shape)"
if ($LASTEXITCODE -ne 0) { throw 'Model setup failed.' }
& '.\.venv\Scripts\python.exe' -X utf8 soundpilot.py train
if ($LASTEXITCODE -ne 0) { throw 'Example indexing failed.' }
& '.\.venv\Scripts\python.exe' -X utf8 setup_context.py
if ($LASTEXITCODE -ne 0) { throw 'Speech model setup failed.' }
