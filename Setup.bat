@echo off
title Yuasa Industrial Scanner - 1-Click Setup & Service Installer
color 0B

echo ========================================================
echo   YUASA BATTERY INDONESIA - INDUSTRIAL SCANNER SERVICE
echo   1-Click Setup ^& Service Installer (Real-App Setup)
echo ========================================================
echo.

REM 1. Memeriksa dan Meminta Hak Administrator secara Otomatis
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Membutuhkan hak akses Administrator...
    echo [INFO] Menampilkan prompt konfirmasi UAC Windows...
    powershell -Command "Start-Process cmd -ArgumentList '/c \"\"%~f0\"\"' -WorkingDirectory \"\"%~dp0\"\" -Verb RunAs"
    exit /b
)

set "ROOT_DIR=%~dp0"
REM Hilangkan trailing slash
if "%ROOT_DIR:~-1%"=="\" set "ROOT_DIR=%ROOT_DIR:~0,-1%"
cd /d "%ROOT_DIR%"

set "NSSM=%ROOT_DIR%\bin\nssm.exe"
set "SERVICE_NAME=YuasaScannerService"
set "LOGS_DIR=%ROOT_DIR%\logs"
if not exist "%LOGS_DIR%" mkdir "%LOGS_DIR%"

echo [1/6] Memeriksa kelengkapan file sistem...
if not exist "%NSSM%" (
    echo.
    echo [ERROR] File nssm.exe tidak ditemukan di:
    echo         %NSSM%
    echo.
    pause
    exit /b 1
)

REM Cek apakah ada executable mandiri atau fallback ke Python
set "TARGET_EXE=%ROOT_DIR%\Yuasa_Scanner_Service.exe"
set "TARGET_ARGS="

if not exist "%TARGET_EXE%" (
    set "TARGET_EXE=%ROOT_DIR%\Yuasa_Scanner_App.exe"
    set "TARGET_ARGS=--service"
)

if not exist "%TARGET_EXE%" (
    REM Fallback ke Python jika exe belum di-build
    where python >nul 2>&1
    if %errorlevel% equ 0 (
        for /f "delims=" %%I in ('where python') do set "PYTHON_PATH=%%I" & goto :found_py
        :found_py
        set "TARGET_EXE=%PYTHON_PATH%"
        set "TARGET_ARGS=\"%ROOT_DIR%\src\service_scanner.py\" --service"
        echo [INFO] Menggunakan Python Environment: %TARGET_EXE%
    ) else (
        echo [ERROR] Tidak ditemukan Yuasa_Scanner_Service.exe maupun Python!
        pause
        exit /b 1
    )
) else (
    echo [INFO] Target Executable: %TARGET_EXE%
)

echo [2/6] Membersihkan file auto-startup lama di Windows...
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
del /f /q "%STARTUP_FOLDER%\Startup_POS_QC1.bat" >nul 2>&1
del /f /q "%STARTUP_FOLDER%\Startup_POS_QC2.bat" >nul 2>&1
del /f /q "%STARTUP_FOLDER%\Jalankan_App.bat" >nul 2>&1
del /f /q "%STARTUP_FOLDER%\Yuasa_Scanner_App.bat" >nul 2>&1

echo [3/6] Menghentikan service lama (jika ada)...
"%NSSM%" stop %SERVICE_NAME% >nul 2>&1
"%NSSM%" remove %SERVICE_NAME% confirm >nul 2>&1
timeout /t 1 /nobreak > nul

REM Otomatis perbarui file exe jika ada build baru
if exist "%ROOT_DIR%\dist\Yuasa_Scanner_Service.exe" (
    copy /y "%ROOT_DIR%\dist\Yuasa_Scanner_Service.exe" "%ROOT_DIR%\Yuasa_Scanner_Service.exe" >nul 2>&1
)
if exist "%ROOT_DIR%\dist\Yuasa_Scanner_App.exe" (
    copy /y "%ROOT_DIR%\dist\Yuasa_Scanner_App.exe" "%ROOT_DIR%\Yuasa_Scanner_App.exe" >nul 2>&1
)

echo [4/6] Memasang Windows Service baru (%SERVICE_NAME%)...
if "%TARGET_ARGS%"=="" (
    "%NSSM%" install %SERVICE_NAME% "%TARGET_EXE%"
) else (
    "%NSSM%" install %SERVICE_NAME% "%TARGET_EXE%" %TARGET_ARGS%
)

"%NSSM%" set %SERVICE_NAME% AppDirectory "%ROOT_DIR%"
"%NSSM%" set %SERVICE_NAME% DisplayName "Yuasa Industrial Scanner & PLC Bridge Service"
"%NSSM%" set %SERVICE_NAME% Description "Layanan latar belakang otomatis integrasi scanner barcode, PLC downtime, printer pallet, masterbox, dan counter baterai PT. Yuasa Battery Indonesia."
"%NSSM%" set %SERVICE_NAME% Start SERVICE_AUTO_START
"%NSSM%" set %SERVICE_NAME% AppStdout "%LOGS_DIR%\service.log"
"%NSSM%" set %SERVICE_NAME% AppStderr "%LOGS_DIR%\service_error.log"
"%NSSM%" set %SERVICE_NAME% AppStdoutCreationDisposition 4
"%NSSM%" set %SERVICE_NAME% AppStderrCreationDisposition 4
"%NSSM%" set %SERVICE_NAME% AppRotateFiles 1
"%NSSM%" set %SERVICE_NAME% AppRotateOnline 1
"%NSSM%" set %SERVICE_NAME% AppRotateBytes 10485760
"%NSSM%" set %SERVICE_NAME% AppRestartDelay 5000

echo [5/6] Membuat 4 Shortcut Pengelolaan di Desktop...
if exist "%ROOT_DIR%\tools\create_shortcuts.vbs" (
    cscript //nologo "%ROOT_DIR%\tools\create_shortcuts.vbs"
) else (
    echo [WARNING] File create_shortcuts.vbs tidak ditemukan.
)

echo [6/6] Menjalankan Windows Service...
"%NSSM%" start %SERVICE_NAME%
timeout /t 2 /nobreak > nul

echo.
echo ========================================================
echo   STATUS INSTALASI WINDOWS SERVICE:
echo ========================================================
"%NSSM%" status %SERVICE_NAME%
echo.
echo ========================================================
echo   [SUKSES] INSTALASI YUASA SCANNER SERVICE SELESAI!
echo.
echo   1. Aplikasi sudah AKTIF 24/7 di background.
echo   2. Operator TIDAK BISA menutup aplikasi ini.
echo   3. Di Desktop sudah tersedia 4 shortcut pengelolaan:
echo      -> [Yuasa] 1. Edit Config       : Ubah IP/Line/Port
echo      -> [Yuasa] 2. Restart Service   : Refresh config baru
echo      -> [Yuasa] 3. Cek Status Service: Pantau live log
echo      -> [Yuasa] 4. Uninstall Service : Copot service
echo ========================================================
echo.
pause
