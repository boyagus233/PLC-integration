@echo off
title Yuasa - Restart Service
color 0E

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
echo   YUASA BATTERY INDONESIA - RESTART SERVICE
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
timeout /t 1 /nobreak > nul

if exist "%ROOT_DIR%\dist\Yuasa_Scanner_Service.exe" (
    echo [2/3] Memperbarui file binary Yuasa_Scanner_Service.exe dari dist...
    copy /y "%ROOT_DIR%\dist\Yuasa_Scanner_Service.exe" "%ROOT_DIR%\Yuasa_Scanner_Service.exe" > nul
    if errorlevel 0 (
        echo       Binary berhasil diperbarui ke versi terbaru!
    )
) else (
    echo [2/3] Tidak ada binary baru di dist, melanjutkan...
)

echo [3/3] Menjalankan kembali YuasaScannerService...
"%NSSM%" start YuasaScannerService

echo.
echo Memeriksa status service...
timeout /t 2 /nobreak > nul
"%NSSM%" status YuasaScannerService

echo.
echo ========================================================
echo   [SUKSES] Service berhasil di-restart!
echo   Aplikasi & konfigurasi terbaru sudah aktif berjalan.
echo ========================================================
echo.
pause
popd
