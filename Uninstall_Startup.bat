@echo off
title Yuasa - Uninstall Auto Startup POS
color 0C

echo ============================================
echo   YUASA BATTERY INDONESIA
echo   Uninstall Auto Startup POS QC 1 ^& QC 2
echo ============================================
echo.

set STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup

echo Memeriksa file startup di folder Windows Startup:
echo %STARTUP_FOLDER%
echo.

set FOUND=0

if exist "%STARTUP_FOLDER%\Startup_POS_QC1.bat" (
    echo [+] Menghapus Startup_POS_QC1.bat ...
    del /f /q "%STARTUP_FOLDER%\Startup_POS_QC1.bat"
    set FOUND=1
)

if exist "%STARTUP_FOLDER%\Startup_POS_QC2.bat" (
    echo [+] Menghapus Startup_POS_QC2.bat ...
    del /f /q "%STARTUP_FOLDER%\Startup_POS_QC2.bat"
    set FOUND=1
)

if exist "%STARTUP_FOLDER%\Jalankan_App.bat" (
    echo [+] Menghapus Jalankan_App.bat ...
    del /f /q "%STARTUP_FOLDER%\Jalankan_App.bat"
    set FOUND=1
)

if exist "%STARTUP_FOLDER%\Yuasa_Scanner_App.bat" (
    echo [+] Menghapus Yuasa_Scanner_App.bat ...
    del /f /q "%STARTUP_FOLDER%\Yuasa_Scanner_App.bat"
    set FOUND=1
)

echo.
if %FOUND%==1 (
    echo ============================================
    echo   [SUKSES] Seluruh file startup lama berhasil dihapus!
    echo   Sekarang Anda bisa menjalankan file Install Startup baru.
    echo ============================================
) else (
    echo ============================================
    echo   [INFO] Tidak ditemukan file Auto Startup lama di folder Startup.
    echo ============================================
)

echo.
pause
