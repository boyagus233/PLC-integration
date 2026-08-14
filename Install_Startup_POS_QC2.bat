@echo off
title Yuasa - Install Auto Startup POS QC 2
color 0B

echo ============================================
echo   YUASA BATTERY INDONESIA
echo   Instalasi Auto Startup POS QC 2
echo ============================================
echo.

set STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set BAT_DEST=%STARTUP_FOLDER%\Startup_POS_QC2.bat

echo Membuat dan menyalin launcher ke folder Windows Startup...

REM Tulis file BAT launcher langsung ke folder Startup
(
    echo @echo off
    echo title Yuasa POS QC 2 - Auto Startup
    echo if exist "D:\PLC\Yuasa_Scanner_App.exe" ^(
    echo     start "" "D:\PLC\Yuasa_Scanner_App.exe"
    echo ^) else ^(
    echo     echo [ERROR] Yuasa_Scanner_App.exe tidak ditemukan di D:\PLC\
    echo     pause
    echo ^)
    echo exit
) > "%BAT_DEST%"

if exist "%BAT_DEST%" (
    echo.
    echo ============================================
    echo   [SUKSES] Instalasi berhasil!
    echo.
    echo   Launcher sudah terpasang di:
    echo   %BAT_DEST%
    echo.
    echo   Mulai sekarang, setiap kali PC dinyalakan:
    echo    -> Yuasa Scanner App akan terbuka otomatis
    echo    -> Koneksi Allen Bradley PLC via LAN otomatis
    echo    -> Tidak perlu klik apapun!
    echo ============================================
    timeout /t 3 /nobreak > nul
) else (
    echo.
    echo [ERROR] Gagal membuat launcher. Coba jalankan
    echo         file ini sebagai Administrator.
    echo         (Klik kanan -> Run as Administrator)
    pause
)

exit
