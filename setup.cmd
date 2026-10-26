@echo off
cd /d "%~dp0"
call :try_python py -3
if not errorlevel 1 goto ready
call :try_python python
if not errorlevel 1 goto ready
call :try_python python3
if not errorlevel 1 goto ready
where uv >nul 2>nul
if errorlevel 1 goto failed
uv venv --python ">=3.12" .venv
if errorlevel 1 goto failed
:ready
".venv\Scripts\python.exe" -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)" >nul 2>nul
if errorlevel 1 goto failed
echo Setup complete. Double-click start.cmd to open the chatbot.
exit /b 0
:failed
echo Setup could not create the Python environment.
echo Install Python 3.12 or newer with the Python launcher or Add Python to PATH enabled.
echo If Python was just installed, close and reopen your terminal or VS Code.
echo You can also install uv and run setup.cmd again.
pause
exit /b 1

:try_python
%* -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)" >nul 2>nul
if errorlevel 1 exit /b 1
%* -m venv .venv
exit /b %errorlevel%
