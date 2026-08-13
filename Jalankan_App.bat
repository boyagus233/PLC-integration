@echo off
title Yuasa Scanner App Launcher
cd /d "%~dp0"

echo Memeriksa aplikasi Yuasa Scanner App...
if exist "Yuasa_Scanner_App.exe" (
    echo Menjalankan aplikasi...
    start "" "Yuasa_Scanner_App.exe"
) else (
    echo Error: File executable Yuasa_Scanner_App.exe tidak ditemukan!
    pause
)
