@echo off
REM Pakistan Trade Data Hub - Windows launcher (Python 3.13, standard library only)
cd /d "%~dp0"
set HOST=127.0.0.1
set PORT=8080
where py >nul 2>nul && (set PY=py -3) || (set PY=python)
start "" cmd /c "timeout /t 3 >nul & start http://localhost:8080"
:loop
%PY% server.py
echo Server stopped (exit %errorlevel%). Restarting in 10 seconds... Close this window to stop.
timeout /t 10 >nul
goto loop
