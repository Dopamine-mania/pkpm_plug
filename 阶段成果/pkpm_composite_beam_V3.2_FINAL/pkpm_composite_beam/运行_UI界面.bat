@echo off
chcp 65001 >nul
echo ========================================
echo  PKPM-CAE Composite Beam Tool - Launch
echo ========================================
echo.
echo Starting UI...
echo.

python ui_main_pro.py

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to start!
    echo.
    echo Possible reasons:
    echo 1. Python not installed or not in PATH
    echo 2. Missing dependencies (run: Install_Dependencies.bat)
    echo.
    pause
) else (
    echo.
    echo [INFO] Program closed normally
)
