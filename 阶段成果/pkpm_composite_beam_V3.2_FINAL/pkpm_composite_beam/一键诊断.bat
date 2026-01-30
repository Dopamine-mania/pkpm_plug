@echo off
cd /d "%~dp0"
setlocal EnableDelayedExpansion

echo [INFO] %date% %time% > diag.log
echo [INFO] AppDir: %~dp0 >> diag.log
echo [INFO] WorkDir: %cd% >> diag.log
echo. >> diag.log

echo ===== where ===== >> diag.log
where py >> diag.log 2>&1
where pyw >> diag.log 2>&1
where python >> diag.log 2>&1
where pythonw >> diag.log 2>&1
echo. >> diag.log

echo ===== env ===== >> diag.log
echo PATH=%PATH% >> diag.log
echo TEMP=%TEMP% >> diag.log
echo. >> diag.log

echo ===== try python import PyQt5 ===== >> diag.log
for /f "delims=" %%P in ('where python 2^>nul') do (
  echo ---- %%P ---- >> diag.log
  "%%P" -c "import sys; print(sys.executable); import PyQt5; print('PyQt5 OK')" >> diag.log 2>&1
)
echo. >> diag.log

echo ===== ui logs ===== >> diag.log
if exist ui_bat.log type ui_bat.log >> diag.log
echo. >> diag.log
if exist "%TEMP%\pkpm_composite_beam_ui.log" type "%TEMP%\pkpm_composite_beam_ui.log" >> diag.log

echo.
echo [INFO] Diagnostic written: diag.log
echo [INFO] Send diag.log back for support.
echo.
pause

