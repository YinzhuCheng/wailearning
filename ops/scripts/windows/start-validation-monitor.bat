@echo off
setlocal
title WAI-VALID-monitor
set "REPO_ROOT=%~dp0..\..\.."
"%REPO_ROOT%\.venv\Scripts\python.exe" "%REPO_ROOT%\ops\scripts\dev\wai_valid_monitor.py"
endlocal
