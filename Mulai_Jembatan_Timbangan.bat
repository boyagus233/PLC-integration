@echo off
:: Self-elevating batch script
NET FILE >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting Administrator privileges...
    powershell -Command "Start-Process -FilePath '%0' -Verb RunAs"
    exit /b
)

title Jembatan Timbangan PLC to Excel
echo Menjalankan jembatan data PLC ke Excel...
python "D:\PLC\src\read_value.py"
pause
