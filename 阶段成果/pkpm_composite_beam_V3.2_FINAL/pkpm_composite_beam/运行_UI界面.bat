@echo off
cd /d "%~dp0"
setlocal EnableDelayedExpansion
echo [INFO] %date% %time% > ui_bat.log
echo [INFO] AppDir: %~dp0 >> ui_bat.log
echo [INFO] WorkDir: %cd% >> ui_bat.log

rem If an EXE build exists, prefer it (no Python required on customer machine)
if exist "dist\PKPM叠合梁工具.exe" (
    echo [INFO] Found EXE: dist\PKPM叠合梁工具.exe >> ui_bat.log
    start "" "dist\PKPM叠合梁工具.exe"
    exit /b 0
)

where py >> ui_bat.log 2>&1
where pyw >> ui_bat.log 2>&1
where python >> ui_bat.log 2>&1
where pythonw >> ui_bat.log 2>&1

if not exist "launch_ui.py" (
    echo [ERROR] launch_ui.py not found in current folder. >> ui_bat.log
    echo [ERROR] launch_ui.py not found. Please re-extract the delivery zip.
    pause
    exit /b 1
)

set "PY_MODE="
set "PY_EXE="

call :pick_pylauncher
if defined PY_MODE goto :launch

call :pick_where_python
if defined PY_EXE goto :launch

echo [ERROR] No usable Python found. >> ui_bat.log
echo [ERROR] Python not found / cannot run. Please install Python 3.x.
echo [INFO] See ui_bat.log for details.
pause
exit /b 1

:launch
if defined PY_MODE (
    where pyw >nul 2>&1
    if !errorlevel!==0 (
        echo [INFO] Selected launcher: pyw -3 >> ui_bat.log
        start "" /min pyw -3 launch_ui.py
        exit /b 0
    ) else (
        echo [INFO] Selected launcher: py -3 >> ui_bat.log
        start "" /min py -3 launch_ui.py
        exit /b 0
    )
) else (
    set "PYW=!PY_EXE:python.exe=pythonw.exe!"
    if exist "!PYW!" (
        echo [INFO] Selected pythonw: !PYW! >> ui_bat.log
        start "" /min "!PYW!" launch_ui.py
        exit /b 0
    ) else (
        echo [INFO] Selected python: !PY_EXE! >> ui_bat.log
        start "" /min "!PY_EXE!" launch_ui.py
        exit /b 0
    )
)
exit /b 0

:pick_pylauncher
where py >nul 2>&1
if not !errorlevel!==0 goto :eof
echo [INFO] Try: py -3 (import PyQt5) >> ui_bat.log
py -3 -c "import PyQt5; print('PyQt5 OK from py')" >> ui_bat.log 2>&1
if !errorlevel!==0 (
    set "PY_MODE=py"
)
goto :eof

:pick_where_python
for /f "delims=" %%P in ('where python 2^>nul') do (
    echo [INFO] Try python: %%P >> ui_bat.log
    echo %%P | find /i "WindowsApps\\python.exe" >nul
    if !errorlevel!==0 (
        echo [INFO] Skip WindowsApps alias: %%P >> ui_bat.log
    ) else (
        "%%P" -c "import PyQt5; print('PyQt5 OK'); import sys; print(sys.executable)" >> ui_bat.log 2>&1
        if !errorlevel!==0 (
            set "PY_EXE=%%P"
            goto :eof
        )
    )
)
goto :eof
