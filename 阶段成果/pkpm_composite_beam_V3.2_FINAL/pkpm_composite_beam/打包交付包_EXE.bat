@echo off
cd /d "%~dp0"
setlocal EnableDelayedExpansion
chcp 65001 >nul
title Package Delivery (EXE)

echo ========================================
echo  Package Delivery (EXE)
echo ========================================
echo.

if not exist "dist\PKPM叠合梁工具.exe" (
  echo [ERROR] dist\PKPM叠合梁工具.exe not found.
  echo Please run build_exe.py / 打包EXE_使用当前Python环境.bat first.
  echo.
  pause
  exit /b 1
)

set "PY=python"
where python >nul 2>&1
if errorlevel 1 (
  where py >nul 2>&1 && set "PY=py -3"
)

echo [INFO] Using: %PY%
%PY% package_delivery.py --mode exe

echo.
pause

