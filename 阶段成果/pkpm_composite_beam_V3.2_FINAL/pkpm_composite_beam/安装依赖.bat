@echo off
echo ========================================
echo  PKPM-CAE Install Dependencies
echo ========================================
echo.
echo Installing Python libraries...
echo.

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo [ERROR] Installation failed!
    echo.
    echo Please check:
    echo 1. Python is installed correctly
    echo 2. Network connection is working
    echo.
) else (
    echo.
    echo [SUCCESS] Dependencies installed!
    echo.
    echo You can now run: 运行_UI界面.bat
)

echo.
pause
