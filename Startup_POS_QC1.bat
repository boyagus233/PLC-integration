@echo off
title Yuasa POS QC 1 - Auto Startup
color 0A

echo ============================================
echo   YUASA BATTERY INDONESIA - POS QC 1
echo   Sistem Otomatis Sedang Dijalankan...
echo ============================================
echo.

echo [1/3] Membuka CX-Programmer...
REM !! EDIT PATH DI BAWAH INI SESUAI LOKASI FILE .CXP DI PC POS QC 1 !!
if exist "C:\Program Files\OMRON\CX-One\CX-Programmer\CXProgrammer.exe" (
    start "" "C:\Program Files\OMRON\CX-One\CX-Programmer\CXProgrammer.exe" "D:\OMRON\project.cxp"
)

echo [2/3] Menunggu CX-Programmer siap (15 detik)...
timeout /t 15 /nobreak > nul

echo [3/3] Membuka Yuasa Scanner App...
if exist "D:\PLC\Yuasa_Scanner_App.exe" (
    start "" "D:\PLC\Yuasa_Scanner_App.exe"
) else (
    echo [ERROR] Yuasa_Scanner_App.exe tidak ditemukan di D:\PLC\
)

echo.
echo ============================================
echo   Sistem POS QC 1 siap digunakan!
echo ============================================
echo.
timeout /t 3 /nobreak > nul
exit
