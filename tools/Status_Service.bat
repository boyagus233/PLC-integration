@echo off
title Yuasa - Status Service & Logs
color 0A

set "TOOLS_DIR=%~dp0"
for %%I in ("%TOOLS_DIR%..") do set "ROOT_DIR=%%~fI"
pushd "%ROOT_DIR%"

set "NSSM=%ROOT_DIR%\bin\nssm.exe"

echo ========================================================
echo   YUASA BATTERY INDONESIA - STATUS SERVICE & LOGS
echo ========================================================
echo.

if not exist "%NSSM%" (
    echo [ERROR] nssm.exe tidak ditemukan di %NSSM%!
    pause
    popd
    exit /b 1
)

echo [STATUS WINDOWS SERVICE]:
"%NSSM%" status YuasaScannerService
echo.

echo ========================================================
echo   20 BARIS LOG TERAKHIR (%ROOT_DIR%\logs\service.log):
echo ========================================================
if exist "%ROOT_DIR%\logs\service.log" (
    powershell -Command "Get-Content '%ROOT_DIR%\logs\service.log' -Tail 20"
) else (
    echo [INFO] Belum ada file log service.log yang tercatat.
)

echo.
echo ========================================================
echo   Tekan tombol apa saja untuk menutup jendela ini...
echo ========================================================
pause > nul
popd
