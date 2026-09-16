@echo off
title Yuasa - Uninstall Service
color 0C

REM Memeriksa hak Administrator
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Meminta hak akses Administrator...
    powershell -Command "Start-Process cmd -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

set "TOOLS_DIR=%~dp0"
for %%I in ("%TOOLS_DIR%..") do set "ROOT_DIR=%%~fI"
pushd "%ROOT_DIR%"

set "NSSM=%ROOT_DIR%\bin\nssm.exe"

echo ========================================================
echo   YUASA BATTERY INDONESIA - UNINSTALL SERVICE
echo ========================================================
echo.

if not exist "%NSSM%" (
    echo [ERROR] nssm.exe tidak ditemukan di %NSSM%!
    pause
    popd
    exit /b 1
)

echo [1/3] Menghentikan YuasaScannerService...
"%NSSM%" stop YuasaScannerService

echo [2/3] Menghapus registrasi Windows Service...
"%NSSM%" remove YuasaScannerService confirm

echo [3/3] Menghapus shortcut dari Desktop...
set "DESKTOP_DIR=%USERPROFILE%\Desktop"
del /f /q "%DESKTOP_DIR%\[Yuasa] 1. Edit Config.lnk" >nul 2>&1
del /f /q "%DESKTOP_DIR%\[Yuasa] 2. Restart Service.lnk" >nul 2>&1
del /f /q "%DESKTOP_DIR%\[Yuasa] 3. Cek Status Service.lnk" >nul 2>&1
del /f /q "%DESKTOP_DIR%\[Yuasa] 4. Uninstall Service.lnk" >nul 2>&1

echo.
echo ========================================================
echo   [SUKSES] YuasaScannerService berhasil dicopot!
echo ========================================================
echo.
pause
popd
