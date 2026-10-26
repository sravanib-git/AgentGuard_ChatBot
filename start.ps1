param([switch]$Test, [switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$pythonExe = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) { throw 'Run setup.cmd first.' }
if ($Test) { & $pythonExe -B -m unittest discover -s test -v }
elseif ($NoBrowser) { & $pythonExe -B run.py --no-browser }
else { & $pythonExe -B run.py }
exit $LASTEXITCODE
