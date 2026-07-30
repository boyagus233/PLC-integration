import requests
import json
import time
import win32print
from datetime import datetime

PRINTER_NAME = "TSC TL241"
TIMBANGAN_WIDTH = 70
TIMBANGAN_HEIGHT = 50
TIMBANGAN_GAP = 2
TIMBANGAN_LINE_NO = "14"

def execute_physical_print_masterbox(code, part_code, batt_type, weight, quantity, date_str, code_production="-"):
    tspl_command = f"""SIZE {TIMBANGAN_WIDTH} mm, {TIMBANGAN_HEIGHT} mm
GAP {TIMBANGAN_GAP} mm, 0 mm
DIRECTION 1
CLS
TEXT 20,20,"0",0,12,12,"PT. YUASA BATTERY INDONESIA"
BAR 20,48,440,3
QRCODE 20,80,M,5,A,0,"{code}"
TEXT 180,75,"0",0,8,8,"{code}"
TEXT 180,115,"0",0,7,7,"Part Code  : {part_code}"
TEXT 180,155,"0",0,7,7,"TYPE       : {batt_type}"
TEXT 180,195,"0",0,7,7,"Quantity   : {quantity} Pcs    BERAT : {weight} KG"
TEXT 180,235,"0",0,7,7,"Prd/Shift/Mc : {date_str}/I/{TIMBANGAN_LINE_NO}"
TEXT 180,270,"0",0,7,7,"Kode Prod    : {code_production}"
PRINT 2
"""
    print(f"[MASTERBOX] Mengirim raw data Master Box ke {PRINTER_NAME}...")
    try:
        hPrinter = win32print.OpenPrinter(PRINTER_NAME)
        try:
            hJob = win32print.StartDocPrinter(hPrinter, 1, ("PLC Auto MasterBox Label", None, "RAW"))
            try:
                win32print.StartPagePrinter(hPrinter)
                win32print.WritePrinter(hPrinter, tspl_command.encode('utf-8'))
                win32print.EndPagePrinter(hPrinter)
                print(f"[MASTERBOX] Sukses mencetak 2 lembar Master Box QR: {code} (KodeProd: {code_production})")
            finally:
                win32print.EndDocPrinter(hPrinter)
        finally:
            win32print.ClosePrinter(hPrinter)
    except Exception as e:
        print(f"[MASTERBOX] Error cetak: {e}")

def test_line(line_no):
    url_timbangan = "https://api.pms.yuasa.seavihive.com/api/fix-scanner-masterbox"
    payload_timbangan = {
        "line_no": line_no,
        "part_code": "M221SDCAC20 B.CH-YTZ5S (Wet-CF) YU-5",
        "weight": 15.44,
        "quantity": 6,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    print(f"\n=== MENCOBA HIT API TIMBANGAN UNTUK LINE {line_no} ===")
    try:
        response = requests.post(url_timbangan, json=payload_timbangan, timeout=10)
        print(f"Status Code: {response.status_code}")
        if response.status_code in [200, 201]:
            res_data = response.json()
            print("Response JSON dari Server:")
            print(json.dumps(res_data, indent=4))
            
            data = res_data.get("data", {})
            code = data.get("code", "MOCK.MB.CODE")
            metadata = data.get("metaData", {})
            raw_part_code = metadata.get("part_code", payload_timbangan["part_code"])
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
                
            code_production = (
                data.get("codeProduction") or 
                data.get("code_production") or 
                res_data.get("codeProduction") or 
                res_data.get("code_production") or 
                metadata.get("codeProduction") or 
                metadata.get("code_production") or 
                "-"
            )
            
            print(f"\n-> MENSTRIGGER PRINT OTOMATIS KE PRINTER TSC TL241...")
            execute_physical_print_masterbox(
                code=code,
                part_code=part_code,
                batt_type=batt_type,
                weight=15.44,
                quantity=6,
                date_str=date_str,
                code_production=code_production
            )
            return True
        else:
            print(f"Respon Error dari Line {line_no}: {response.text}")
            return False
    except Exception as e:
        print(f"Error Request: {e}")
        return False

# Main execution
success = test_line("14")
if not success:
    print("Mencoba Line 1...")
    test_line("1")
