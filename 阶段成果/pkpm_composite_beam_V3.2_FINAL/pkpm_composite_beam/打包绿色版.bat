@echo off
chcp 65001 >nul
echo ============================================================
echo PKPM-CAE Composite Beam Tool - Build Portable Version
echo ============================================================
echo.
echo This will create a standalone .exe file (50-80 MB)
echo No Python installation required on target computers
echo.
echo Starting PyInstaller build...
echo.

python build_portable.py

echo.
echo ============================================================
echo Build process completed. Check messages above for status.
echo ============================================================
echo.
pause
