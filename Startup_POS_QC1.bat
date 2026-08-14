@echo off
title Yuasa POS QC 1 - Auto Startup
color 0A

echo ============================================
echo   YUASA BATTERY INDONESIA - POS QC 1
echo   Sistem Otomatis Sedang Dijalankan...
echo ============================================
echo.

echo Membuka Yuasa Scanner App...
if exist "D:\PLC\Yuasa_Scanner_App.exe" (
    start "" "D:\PLC\Yuasa_Scanner_App.exe"
) else (
    echo [ERROR] Yuasa_Scanner_App.exe tidak ditemukan di D:\PLC\
    pause
)

timeout /t 2 /nobreak > nul
exit
