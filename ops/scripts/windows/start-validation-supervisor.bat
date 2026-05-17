@echo off
setlocal
title WAI-VALID-supervisor
set "REPO_ROOT=%~dp0..\..\.."
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File "%REPO_ROOT%\ops\scripts\windows\start-validation-supervisor-detached.ps1" %*
endlocal
