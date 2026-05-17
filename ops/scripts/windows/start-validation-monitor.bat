@echo off
setlocal
set "REPO_ROOT=%~dp0..\..\.."
set "RUN_ID=%~1"
if "%RUN_ID%"=="" (
  "%REPO_ROOT%\.venv\Scripts\python.exe" "%REPO_ROOT%\ops\scripts\dev\wai_valid_windows_launcher.py" monitor
) else (
  "%REPO_ROOT%\.venv\Scripts\python.exe" "%REPO_ROOT%\ops\scripts\dev\wai_valid_windows_launcher.py" monitor --run-id "%RUN_ID%"
)
endlocal
