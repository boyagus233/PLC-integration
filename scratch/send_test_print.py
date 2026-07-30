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
TEXT 20,15,"2",0,1,1,"PT. YUASA BATTERY INDONESIA"
BAR 20,40,330,3
QRCODE 18,70,M,4,A,0,"{code}"
TEXT 155,55,"1",0,1,1,"Group Code : {code}"
TEXT 155,90,"1",0,1,1,"Order No.  : -"
TEXT 155,125,"1",0,1,1,"Customer   : AFM (PT. SANTI YOGA)"
TEXT 155,160,"1",0,1,1,"Part Code  : {part_code}"
TEXT 155,195,"1",0,1,1,"Batt. Type : {batt_type}"
TEXT 155,230,"1",0,1,1,"Quantity   : {quantity}"
TEXT 155,265,"1",0,1,1,"Prod. /Shift/Mc : {date_str}/I/{PRINTER_LABEL_LINE_NO}"
PRINT 1
"""
    print(f"Sending Pallet Clean Borderless Test Print to {PRINTER_NAME}...")
    hPrinter = win32print.OpenPrinter(PRINTER_NAME)
    try:
        hJob = win32print.StartDocPrinter(hPrinter, 1, ("Test Print Pallet Clean", None, "RAW"))
        try:
            win32print.StartPagePrinter(hPrinter)
            win32print.WritePrinter(hPrinter, tspl_command.encode('utf-8'))
            win32print.EndPagePrinter(hPrinter)
            print("Pallet Test Print Sent Successfully!")
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
TEXT 20,15,"2",0,1,1,"PT. YUASA BATTERY INDONESIA"
BAR 20,40,330,3
QRCODE 18,70,M,4,A,0,"{code}"
TEXT 155,65,"2",0,1,1,"{code}"
TEXT 155,110,"1",0,1,1,"Part Code  : {part_code}"
TEXT 155,150,"1",0,1,1,"TYPE       : {batt_type}"
TEXT 155,190,"1",0,1,1,"Quantity   : {quantity} Pcs    BERAT : {weight} KG"
TEXT 155,230,"1",0,1,1,"Prd/Shift/Mc : {date_str}/I/{TIMBANGAN_LINE_NO}"
PRINT 1
"""
    print(f"Sending MasterBox Clean Borderless Test Print to {PRINTER_NAME}...")
    hPrinter = win32print.OpenPrinter(PRINTER_NAME)
    try:
        hJob = win32print.StartDocPrinter(hPrinter, 1, ("Test Print MasterBox Clean", None, "RAW"))
        try:
            win32print.StartPagePrinter(hPrinter)
            win32print.WritePrinter(hPrinter, tspl_command.encode('utf-8'))
            win32print.EndPagePrinter(hPrinter)
            print("MasterBox Test Print Sent Successfully!")
        finally:
            win32print.EndDocPrinter(hPrinter)
    finally:
        win32print.ClosePrinter(hPrinter)

if __name__ == "__main__":
    send_masterbox_test()
    send_pallet_test()
