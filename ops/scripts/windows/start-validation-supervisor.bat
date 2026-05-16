@echo off
setlocal
title WAI-VALID-supervisor
set "REPO_ROOT=%~dp0..\..\.."
"%REPO_ROOT%\.venv\Scripts\python.exe" "%REPO_ROOT%\ops\scripts\dev\wai_valid_supervisor.py" %*
endlocal
