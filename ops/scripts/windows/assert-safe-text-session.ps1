<#
.SYNOPSIS
Assert that the current Windows PowerShell session is using the repository safe-text workflow.

.DESCRIPTION
This helper is meant for operators or agents who want a quick yes/no check
before inspecting multilingual repository files. It verifies the environment
marker set by enter-safe-text-session.ps1 and prints a short status summary.

.EXAMPLE
. .\ops\scripts\windows\enter-safe-text-session.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ops\scripts\windows\assert-safe-text-session.ps1
#>

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$sessionReady = $env:COURSEEVAL_SAFE_TEXT_SESSION -eq '1'

if (-not $sessionReady) {
    Write-Error 'Safe text session is not active. Run ops\scripts\windows\enter-safe-text-session.ps1 first.'
}

Write-Output 'Safe text session is active.'
Write-Output "Console.OutputEncoding=$([Console]::OutputEncoding.WebName)"
Write-Output "Console.InputEncoding=$([Console]::InputEncoding.WebName)"
Write-Output "PYTHONUTF8=$env:PYTHONUTF8"
Write-Output "PYTHONIOENCODING=$env:PYTHONIOENCODING"
