@echo off
title Yuasa - Install Auto Startup POS QC 1
color 0E

echo ============================================
echo   YUASA BATTERY INDONESIA
echo   Instalasi Auto Startup POS QC 1
echo ============================================
echo.

REM Dapatkan path folder Startup Windows untuk user yang sedang login
set STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set BAT_SOURCE=%~dp0Startup_POS_QC1.bat
set BAT_DEST=%STARTUP_FOLDER%\Startup_POS_QC1.bat

echo Memverifikasi file launcher...
if not exist "%BAT_SOURCE%" (
    echo.
    echo [ERROR] File Startup_POS_QC1.bat tidak ditemukan!
    echo         Pastikan Install_Startup_POS_QC1.bat dan
    echo         Startup_POS_QC1.bat ada di folder yang sama.
    echo.
    pause
    exit /b 1
)

echo File launcher ditemukan: %BAT_SOURCE%
echo.
echo Menyalin ke folder Windows Startup...
copy /Y "%BAT_SOURCE%" "%BAT_DEST%"

if exist "%BAT_DEST%" (
    echo.
    echo ============================================
    echo   [SUKSES] Instalasi berhasil!
    echo.
    echo   Startup_POS_QC1.bat sudah terpasang di:
    echo   %BAT_DEST%
    echo.
    echo   Mulai sekarang, setiap kali PC dinyalakan:
    echo    -> CX-Programmer akan terbuka otomatis
    echo    -> Yuasa Scanner App akan terbuka otomatis
    echo    -> Tidak perlu klik apapun!
    echo ============================================
    timeout /t 3 /nobreak > nul
) else (
    echo.
    echo [ERROR] Gagal menyalin file. Coba jalankan
    echo         file ini sebagai Administrator.
    echo         (Klik kanan -> Run as Administrator)
    pause
)

exit
