import win32print

PRINTER_NAME = "TSC TL241"

# Master Box TSPL command (Normal top-aligned, Y=20 start, PRINT 2, includes Kode Prod)
tspl_masterbox = """SIZE 70 mm, 50 mm
GAP 2 mm, 0 mm
DIRECTION 1
CLS
TEXT 20,20,"0",0,12,12,"PT. YUASA BATTERY INDONESIA"
BAR 20,48,440,3
QRCODE 20,80,M,5,A,0,"YBID.MB.260728.14.000001"
TEXT 180,75,"0",0,8,8,"YBID.MB.260728.14.000001"
TEXT 180,115,"0",0,7,7,"Part Code  : M221SDCAC20"
TEXT 180,155,"0",0,7,7,"TYPE       : B.CH-YTZ5S (Wet-CF) YU-5"
TEXT 180,195,"0",0,7,7,"Quantity   : 10 Pcs    BERAT : 15.44 KG"
TEXT 180,235,"0",0,7,7,"Prd/Shift/Mc : 28-Jul-2026/I/14"
TEXT 180,270,"0",0,7,7,"Kode Prod    : 260728140001"
PRINT 2
"""

print(f"Sending Master Box Test Print (Reprint Layout) to '{PRINTER_NAME}'...")
try:
    hPrinter = win32print.OpenPrinter(PRINTER_NAME)
    try:
        hJob = win32print.StartDocPrinter(hPrinter, 1, ("Master Box Reprint Test", None, "RAW"))
        try:
            win32print.StartPagePrinter(hPrinter)
            win32print.WritePrinter(hPrinter, tspl_masterbox.encode('utf-8'))
            win32print.EndPagePrinter(hPrinter)
            print("Successfully sent Master Box Test Print (2 copies)!")
        finally:
            win32print.EndDocPrinter(hPrinter)
    finally:
        win32print.ClosePrinter(hPrinter)
except Exception as e:
    print(f"Print failed: {e}")
