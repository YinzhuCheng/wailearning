@echo off
setlocal
set "REPO_ROOT=%~dp0..\..\.."
"%REPO_ROOT%\.venv\Scripts\python.exe" "%REPO_ROOT%\ops\scripts\dev\wai_valid_windows_launcher.py" background "%REPO_ROOT%\ops\scripts\windows\start-validation-supervisor-detached.ps1" %*
endlocal
