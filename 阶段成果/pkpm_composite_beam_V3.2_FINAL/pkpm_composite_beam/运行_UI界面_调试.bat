@echo off
cd /d "%~dp0"
echo.

set "PY_CMD="
where python >nul 2>&1 && set "PY_CMD=python"
if not defined PY_CMD (
    where py >nul 2>&1 && set "PY_CMD=py -3"
)
if not defined PY_CMD (
    echo [ERROR] Python not found. Please install Python 3.x or add it to PATH.
    echo.
    pause
    exit /b 1
)

echo [INFO] Using: %PY_CMD%
echo [INFO] WorkDir: %cd%
echo.
echo [INFO] Checking PyQt5...
%PY_CMD% -c "import sys; print('exe:', sys.executable); import PyQt5; print('PyQt5 OK')" || (
    echo.
    echo [ERROR] PyQt5 missing. Please run: 安装依赖.bat
    echo.
    pause
    exit /b 1
)

echo.
echo [INFO] Launching UI in console mode (keeps window open)...
echo [INFO] If it crashes, copy the traceback and send it back.
echo.
%PY_CMD% launch_ui.py

echo.
echo [INFO] UI process exited.
echo [INFO] If you see no UI, check ui_error.log (same folder).
echo.
pause
