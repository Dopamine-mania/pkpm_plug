@echo off
cd /d "%~dp0"
setlocal EnableDelayedExpansion
chcp 65001 >nul
title Build EXE (Use Existing Python)

echo ========================================
echo  Build Windows EXE (Use Existing Python)
echo ========================================
echo.
echo [INFO] This mode does NOT create venv and does NOT pip install.
echo [INFO] It uses an existing Python that already has: PyQt5 + PyInstaller.
echo.

rem Avoid mixing user-site packages (can break PyInstaller analysis on some machines)
set "PYTHONNOUSERSITE=1"
set "PYTHONPATH="

set "LOG=build_exe.log"
echo [INFO] %date% %time% > "%LOG%"
echo [INFO] AppDir: %~dp0 >> "%LOG%"
echo [INFO] WorkDir: %cd% >> "%LOG%"
echo [INFO] PYTHONNOUSERSITE=%PYTHONNOUSERSITE% >> "%LOG%"

set "PY="

rem 1) Prefer a known Anaconda location (common on dev machines)
if exist "D:\Study\Anaconda\python.exe" (
  set "PY=D:\Study\Anaconda\python.exe"
  echo [INFO] Prefer Anaconda: !PY! >> "%LOG%"
)

if defined PY goto :gotpython

rem 2) Otherwise, scan PATH python list
if not defined PY (
  for /f "delims=" %%P in ('where python 2^>nul') do (
    echo %%P | find /i "WindowsApps\\python.exe" >nul
    if !errorlevel!==0 (
      echo [INFO] Skip WindowsApps alias: %%P >> "%LOG%"
    ) else (
      echo [INFO] Probe: %%P >> "%LOG%"
      "%%P" -c "import PyQt5, PyInstaller; import sys; print(sys.executable)" >> "%LOG%" 2>&1
      if !errorlevel!==0 (
        set "PY=%%P"
        goto :gotpython
      )
    )
  )
)

:gotpython
if not defined PY (
  echo [ERROR] No usable python found (need PyQt5 + PyInstaller). >> "%LOG%"
  echo.
  echo [ERROR] No usable python found.
  echo You need a Python that can import PyQt5 and PyInstaller.
  echo Tip: open Anaconda Prompt (base) and run:
  echo   python -c "import PyQt5, PyInstaller; print('OK')"
  echo.
  echo [INFO] See: %LOG%
  pause
  exit /b 1
)

echo [INFO] Using python: %PY%
echo [INFO] Using python: %PY% >> "%LOG%"

echo.
echo [INFO] Cleaning old dist/build...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul

echo.
echo [INFO] Building EXE...
echo [INFO] Run: "%PY%" build_exe.py >> "%LOG%"
"%PY%" build_exe.py >> "%LOG%" 2>&1
echo [INFO] build_exe.py exitcode=%errorlevel% >> "%LOG%"

if errorlevel 1 (
  echo.
  echo [ERROR] Build failed. See: %LOG%
  echo.
  pause
  exit /b 1
)

echo.
echo [SUCCESS] Built: dist\PKPM叠合梁工具.exe
echo [INFO] Log: %LOG%
echo.
pause

