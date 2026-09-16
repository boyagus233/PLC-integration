@echo off
title Yuasa - Edit Konfigurasi (config.ini)
color 0B

echo ========================================================
echo   YUASA BATTERY INDONESIA - EDIT KONFIGURASI
echo ========================================================
echo.
echo Membuka file config.ini di Notepad...
echo.

set "TOOLS_DIR=%~dp0"
for %%I in ("%TOOLS_DIR%..") do set "ROOT_DIR=%%~fI"
set "CONFIG_PATH=%ROOT_DIR%\config.ini"

start notepad.exe "%CONFIG_PATH%"

echo ========================================================
echo   [PETUNJUK SETELAH EDIT CONFIG]
echo   1. Silakan ubah IP, Line No, atau Port sesuai kebutuhan.
echo   2. Tekan Ctrl+S (Save) di Notepad, lalu tutup Notepad.
echo   3. Klik shortcut "[Yuasa] 2. Restart Service" di Desktop
echo      agar pengaturan baru langsung aktif!
echo ========================================================
echo.
pause
