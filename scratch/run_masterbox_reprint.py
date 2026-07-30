import requests
import json
import time
import win32print
from datetime import datetime

PRINTER_NAME = "TSC TL241"
TIMBANGAN_WIDTH = 70
TIMBANGAN_HEIGHT = 50
TIMBANGAN_GAP = 2

def execute_physical_print_masterbox(code, part_code, batt_type, weight, quantity, date_str, code_production="-", line_no="14"):
    tspl_command = f"""SIZE {TIMBANGAN_WIDTH} mm, {TIMBANGAN_HEIGHT} mm
GAP {TIMBANGAN_GAP} mm, 0 mm
DIRECTION 1
CLS
TEXT 20,40,"0",0,12,12,"PT. YUASA BATTERY INDONESIA"
BAR 20,68,440,3
QRCODE 20,100,M,5,A,0,"{code}"
TEXT 180,95,"0",0,8,8,"{code}"
TEXT 180,135,"0",0,7,7,"Part Code  : {part_code}"
TEXT 180,175,"0",0,7,7,"TYPE       : {batt_type}"
TEXT 180,215,"0",0,7,7,"Quantity   : {quantity} Pcs    BERAT : {weight} KG"
TEXT 180,255,"0",0,7,7,"Prd/Shift/Mc : {date_str}/I/{line_no}"
TEXT 180,290,"0",0,7,7,"Kode Prod    : {code_production}"
PRINT 2
"""
    print(f"[REPRINT] Mengirim raw data Master Box ke {PRINTER_NAME}...")
    try:
        hPrinter = win32print.OpenPrinter(PRINTER_NAME)
        try:
            hJob = win32print.StartDocPrinter(hPrinter, 1, ("Master Box Reprint", None, "RAW"))
            try:
                win32print.StartPagePrinter(hPrinter)
                win32print.WritePrinter(hPrinter, tspl_command.encode('utf-8'))
                win32print.EndPagePrinter(hPrinter)
                print(f"[REPRINT] Sukses mencetak 2 lembar Reprint Master Box: {code} (KodeProd: {code_production})")
            finally:
                win32print.EndDocPrinter(hPrinter)
        finally:
            win32print.ClosePrinter(hPrinter)
    except Exception as e:
        print(f"[REPRINT] Error cetak: {e}")

def trigger_reprint(line_no):
    url_retry = "https://api.pms.yuasa.seavihive.com/api/fix-scanner-masterbox-retry"
    payload = {"line_no": line_no}
    print(f"\n=== TRIGERRING MASTER BOX REPRINT API UNTUK LINE {line_no} ===")
    try:
        response = requests.post(url_retry, json=payload, timeout=10)
        print(f"Status Code: {response.status_code}")
        if response.status_code in [200, 201]:
            res_data = response.json()
            print("Response JSON dari Server:")
            print(json.dumps(res_data, indent=4))
            
            data = res_data.get("data", {})
            code = data.get("code", "MOCK.MB.REPRINT")
            metadata = data.get("metaData", {})
            raw_part_code = metadata.get("part_code", "-")
            parts = [p.strip() for p in raw_part_code.split(" ") if p.strip()]
            part_code = parts[0] if parts else raw_part_code
            batt_type = " ".join(parts[1:]) if len(parts) >= 2 else "-"
            
            created_at_raw = data.get("createdAt", "")
            try:
                dt_part = created_at_raw.split(".")[0]
                dt = datetime.strptime(dt_part, "%Y-%m-%dT%H:%M:%S")
                date_str = dt.strftime("%d-%b-%Y")
            except:
                date_str = datetime.now().strftime("%d-%b-%Y")
                
            weight = metadata.get("weight", "0.0")
            quantity = metadata.get("quantity", "0")
            code_production = (
                data.get("codeProduction") or 
                data.get("code_production") or 
                res_data.get("codeProduction") or 
                res_data.get("code_production") or 
                metadata.get("codeProduction") or 
                metadata.get("code_production") or 
                "-"
            )
            
            print(f"\n-> MENSTRIGGER PRINT REPRINT OTOMATIS KE PRINTER TSC TL241...")
            execute_physical_print_masterbox(
                code=code,
                part_code=part_code,
                batt_type=batt_type,
                weight=weight,
                quantity=quantity,
                date_str=date_str,
                code_production=code_production,
                line_no=line_no
            )
            return True
        else:
            print(f"Respon Error dari Line {line_no}: {response.text}")
            return False
    except Exception as e:
        print(f"Error Request: {e}")
        return False

# Execute reprint on line 1 (the line where transaction was completed)
success = trigger_reprint("1")
if not success:
    trigger_reprint("14")
