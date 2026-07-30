import win32print

PRINTER_NAME = "TSC TL241"
PRINTER_WIDTH = 70
PRINTER_HEIGHT = 50
PRINTER_GAP = 2
PRINTER_LABEL_LINE_NO = "14"
TIMBANGAN_WIDTH = 70
TIMBANGAN_HEIGHT = 50
TIMBANGAN_GAP = 2
TIMBANGAN_LINE_NO = "14"

def send_pallet_test():
    code = "YBID.PLT.250908.000001"
    part_code = "M221SDCAC20"
    batt_type = "B.CH-YTZ5S (Wet-CF) YU-5"
    quantity = "640 PCS - 64 Pack"
    date_str = "25-Sep-2025"

    tspl_command = f"""SIZE {PRINTER_WIDTH} mm, {PRINTER_HEIGHT} mm
GAP {PRINTER_GAP} mm, 0 mm
DIRECTION 1
CLS
TEXT 20,100,"0",0,12,12,"PT. YUASA BATTERY INDONESIA"
BAR 20,128,440,3
QRCODE 20,160,M,5,A,0,"{code}"
TEXT 180,155,"0",0,7,7,"Group Code : {code}"
TEXT 180,188,"0",0,7,7,"Order No.  : -"
TEXT 180,221,"0",0,7,7,"Customer   : AFM (PT. SANTI YOGA)"
TEXT 180,254,"0",0,7,7,"Part Code  : {part_code}"
TEXT 180,287,"0",0,7,7,"Batt. Type : {batt_type}"
TEXT 180,320,"0",0,7,7,"Quantity   : {quantity}"
TEXT 180,353,"0",0,7,7,"Prod. /Shift/Mc : {date_str}/I/{PRINTER_LABEL_LINE_NO}"
PRINT 1
"""
    print(f"Sending Pallet Shifted Down Test (Y=100) to {PRINTER_NAME}...")
    hPrinter = win32print.OpenPrinter(PRINTER_NAME)
    try:
        hJob = win32print.StartDocPrinter(hPrinter, 1, ("Pallet Shifted Down Test Y=100", None, "RAW"))
        try:
            win32print.StartPagePrinter(hPrinter)
            win32print.WritePrinter(hPrinter, tspl_command.encode('utf-8'))
            win32print.EndPagePrinter(hPrinter)
            print("Pallet Test Sent!")
        finally:
            win32print.EndDocPrinter(hPrinter)
    finally:
        win32print.ClosePrinter(hPrinter)

def send_masterbox_test():
    code = "YBID.MB.250908.08.000001"
    part_code = "M221SDCAC20"
    batt_type = "B.CH-YTZ5S (Wet-CF) YU-5"
    weight = "15.44"
    quantity = "10"
    date_str = "25-Sep-2025"

    tspl_command = f"""SIZE {TIMBANGAN_WIDTH} mm, {TIMBANGAN_HEIGHT} mm
GAP {TIMBANGAN_GAP} mm, 0 mm
DIRECTION 1
CLS
TEXT 20,100,"0",0,12,12,"PT. YUASA BATTERY INDONESIA"
BAR 20,128,440,3
QRCODE 20,160,M,5,A,0,"{code}"
TEXT 180,155,"0",0,8,8,"{code}"
TEXT 180,195,"0",0,7,7,"Part Code  : {part_code}"
TEXT 180,235,"0",0,7,7,"TYPE       : {batt_type}"
TEXT 180,275,"0",0,7,7,"Quantity   : {quantity} Pcs    BERAT : {weight} KG"
TEXT 180,315,"0",0,7,7,"Prd/Shift/Mc : {date_str}/I/{TIMBANGAN_LINE_NO}"
PRINT 2
"""
    print(f"Sending MasterBox Shifted Down Test (Y=100) to {PRINTER_NAME}...")
    hPrinter = win32print.OpenPrinter(PRINTER_NAME)
    try:
        hJob = win32print.StartDocPrinter(hPrinter, 1, ("MasterBox Shifted Down Test Y=100", None, "RAW"))
        try:
            win32print.StartPagePrinter(hPrinter)
            win32print.WritePrinter(hPrinter, tspl_command.encode('utf-8'))
            win32print.EndPagePrinter(hPrinter)
            print("MasterBox Test Sent!")
        finally:
            win32print.EndDocPrinter(hPrinter)
    finally:
        win32print.ClosePrinter(hPrinter)

if __name__ == "__main__":
    send_pallet_test()
    send_masterbox_test()
