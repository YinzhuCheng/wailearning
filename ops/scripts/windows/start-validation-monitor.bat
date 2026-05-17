@echo off
setlocal
title WAI-VALID-monitor
set "REPO_ROOT=%~dp0..\..\.."
set "MONITOR_PID_FILE=%REPO_ROOT%\.agent-run\validation-daemon\WAI-VALID-monitor.pid"
"%SystemRoot%\System32\taskkill.exe" /FI "WINDOWTITLE eq WAI-VALID-monitor" /T /F >nul 2>nul
set "RUN_ID=%~1"
if "%RUN_ID%"=="" (
  "%REPO_ROOT%\.venv\Scripts\python.exe" "%REPO_ROOT%\ops\scripts\dev\wai_valid_register_current_run.py" >nul 2>nul
) else (
  "%REPO_ROOT%\.venv\Scripts\python.exe" "%REPO_ROOT%\ops\scripts\dev\wai_valid_register_current_run.py" --run-id "%RUN_ID%" >nul 2>nul
)
if exist "%MONITOR_PID_FILE%" (
  for /f "usebackq delims=" %%P in ("%MONITOR_PID_FILE%") do (
    if not "%%P"=="" (
      "%SystemRoot%\System32\taskkill.exe" /PID %%P /T /F >nul 2>nul
    )
  )
)
if "%RUN_ID%"=="" (
  "%REPO_ROOT%\.venv\Scripts\python.exe" -u "%REPO_ROOT%\ops\scripts\dev\wai_valid_monitor.py"
) else (
  "%REPO_ROOT%\.venv\Scripts\python.exe" -u "%REPO_ROOT%\ops\scripts\dev\wai_valid_monitor.py" --run-id "%RUN_ID%"
)
endlocal
