# No activation or execution-policy changes are needed by this script.
$ErrorActionPreference = 'Stop'
$env:PYTHONDONTWRITEBYTECODE = '1'
$dockerSmoke = $args -ccontains 'docker-smoke'
$pythonArgs = @()
if ($env:SOLY_PYTHON) {
    $python = $env:SOLY_PYTHON
} elseif (-not $dockerSmoke -and (Test-Path -LiteralPath (Join-Path $PSScriptRoot '.venv/Scripts/python.exe'))) {
    $python = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
} elseif (-not $dockerSmoke -and (Test-Path -LiteralPath (Join-Path $PSScriptRoot '.venv/bin/python'))) {
    $python = Join-Path $PSScriptRoot '.venv/bin/python'
} elseif (Get-Command py -CommandType Application -ErrorAction SilentlyContinue) {
    $python = 'py'
    $pythonArgs = @('-3.12')
} elseif (Get-Command python3.12 -CommandType Application -ErrorAction SilentlyContinue) {
    $python = 'python3.12'
} elseif (Get-Command python3 -CommandType Application -ErrorAction SilentlyContinue) {
    $python = 'python3'
} elseif (Get-Command python -CommandType Application -ErrorAction SilentlyContinue) {
    $python = 'python'
} else {
    [Console]::Error.WriteLine('Python is missing. Install Python 3.12.15; set SOLY_PYTHON to its executable path.')
    exit 1
}
try {
    & $python @pythonArgs (Join-Path $PSScriptRoot 'scripts/dev.py') @args
    exit $LASTEXITCODE
} catch {
    [Console]::Error.WriteLine("Cannot run Python: $_. Set SOLY_PYTHON to its executable path.")
    exit 1
}
