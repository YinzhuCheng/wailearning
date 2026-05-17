param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $SupervisorArgs
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
$scriptPath = Join-Path $repoRoot "ops\scripts\dev\wai_valid_supervisor.py"

if (-not (Test-Path $pythonExe)) {
    throw "Missing repository venv interpreter: $pythonExe"
}

if (-not (Test-Path $scriptPath)) {
    throw "Missing supervisor script: $scriptPath"
}

$argumentList = @($scriptPath) + $SupervisorArgs

Start-Process `
    -FilePath $pythonExe `
    -ArgumentList @('-u') + $argumentList `
    -WorkingDirectory $repoRoot `
    -WindowStyle Hidden
