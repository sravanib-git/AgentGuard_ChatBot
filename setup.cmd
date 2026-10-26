@echo off
cd /d "%~dp0"
where uv >nul 2>nul
if errorlevel 1 goto standard
uv venv --python 3.12 .venv
if errorlevel 1 goto failed
exit /b 0
:standard
py -3.12 -m venv .venv
if errorlevel 1 goto failed
exit /b 0
:failed
echo Install Python 3.12 or uv, then run setup.cmd again.
pause
exit /b 1
