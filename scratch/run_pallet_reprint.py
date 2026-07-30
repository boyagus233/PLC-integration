import requests
import json
import win32print
from datetime import datetime

PRINTER_NAME = "TSC TL241"
PRINTER_WIDTH = 70
PRINTER_HEIGHT = 50
PRINTER_GAP = 2
PRINTER_LABEL_LINE_NO = "01"

def execute_physical_print_pallet(data_dict):
    code = data_dict.get("code", "-")
    part_code = data_dict.get("part_code", "-")
    batt_type = data_dict.get("batt_type", "-")
    quantity = data_dict.get("quantity", "0")
    date_str = data_dict.get("date_str", "-")
    customer = data_dict.get("customer", "AFM (PT. SANTI YOGA)")
    order_no = data_dict.get("order_no", "-")
    
    tspl_command = f"""SIZE {PRINTER_WIDTH} mm, {PRINTER_HEIGHT} mm
GAP {PRINTER_GAP} mm, 0 mm
DIRECTION 1
CLS
TEXT 20,100,"0",0,12,12,"PT. YUASA BATTERY INDONESIA"
BAR 20,128,440,3
QRCODE 20,160,M,5,A,0,"{code}"
TEXT 180,155,"0",0,7,7,"Group Code : {code}"
TEXT 180,188,"0",0,7,7,"Order No.  : {order_no}"
TEXT 180,221,"0",0,7,7,"Customer   : {customer}"
TEXT 180,254,"0",0,7,7,"Part Code  : {part_code}"
TEXT 180,287,"0",0,7,7,"Batt. Type : {batt_type}"
TEXT 180,320,"0",0,7,7,"Quantity   : {quantity}"
TEXT 180,353,"0",0,7,7,"Prod. /Shift/Mc : {date_str}/I/{PRINTER_LABEL_LINE_NO}"
PRINT 1
"""
    print(f"[PALLET] Mengirim raw data Pallet ke {PRINTER_NAME}...")
    try:
        hPrinter = win32print.OpenPrinter(PRINTER_NAME)
        try:
            hJob = win32print.StartDocPrinter(hPrinter, 1, ("Pallet Label Print", None, "RAW"))
            try:
                win32print.StartPagePrinter(hPrinter)
                win32print.WritePrinter(hPrinter, tspl_command.encode('utf-8'))
                win32print.EndPagePrinter(hPrinter)
                print(f"[PALLET] Sukses mencetak Pallet QR: {code}")
            finally:
                win32print.EndDocPrinter(hPrinter)
        finally:
            win32print.ClosePrinter(hPrinter)
    except Exception as e:
        print(f"[PALLET] Error cetak: {e}")

url_pallet_retry = "https://api.pms.yuasa.seavihive.com/api/fix-scanner-pallet-retry"
payload = {"line_no": "1"}

print("Hitting Pallet Retry API for Line 1 and printing label...")
try:
    res = requests.post(url_pallet_retry, json=payload, timeout=10)
    print(f"Status Code: {res.status_code}")
    if res.status_code in [200, 201]:
        res_data = res.json()
        data = res_data.get("data", {})
        metadata = data.get("metaData", {})
        
        created_at_raw = data.get("createdAt", "")
        try:
            dt_part = created_at_raw.split(".")[0]
            dt = datetime.strptime(dt_part, "%Y-%m-%dT%H:%M:%S")
            date_str = dt.strftime("%d-%b-%Y")
        except:
            date_str = datetime.now().strftime("%d-%b-%Y")
            
        raw_part_code = metadata.get("part_code", res_data.get("partCode", "-"))
        parts = [p.strip() for p in raw_part_code.split(" ") if p.strip()]
        if len(parts) >= 2:
            part_code = parts[0]
            batt_type = " ".join(parts[1:])
        else:
            part_code = raw_part_code
            batt_type = "-"
            
        customer = (
            metadata.get("customer") or 
            metadata.get("customer_name") or 
            data.get("customer") or 
            res_data.get("customer") or 
            res_data.get("customerName") or 
            res_data.get("customer_name") or 
            "AFM (PT. SANTI YOGA)"
        )
        order_no = (
            metadata.get("order_no") or 
            metadata.get("no_order") or 
            data.get("order_no") or 
            res_data.get("orderNo") or 
            res_data.get("order_no") or 
            res_data.get("no_order") or 
            "-"
        )
        
        pack_qty = (
            res_data.get("quantityPack") or 
            data.get("quantityPack") or 
            metadata.get("quantityPack") or 
            metadata.get("quantity_pack") or 
            metadata.get("masterbox") or 
            None
        )
        pcs_qty = (
            res_data.get("quantityPcs") or 
            data.get("quantityPcs") or 
            metadata.get("quantityPcs") or 
            metadata.get("quantity_pcs") or 
            metadata.get("quantity") or 
            None
        )
        
        if pack_qty is not None and pcs_qty is not None:
            quantity_formatted = f"{pack_qty} Masterbox / {pcs_qty} Pcs"
        elif pcs_qty is not None:
            quantity_formatted = f"{pcs_qty} Pcs"
        else:
            quantity_formatted = str(metadata.get("quantity", "0 Pcs"))
            
        parsed_data = {
            "code": data.get("code", "-"),
            "part_code": part_code,
            "batt_type": batt_type,
            "quantity": quantity_formatted,
            "date_str": date_str,
            "customer": customer,
            "order_no": order_no
        }
        
        print(f"Parsed Pallet Data: {parsed_data}")
        print("\n-> MENSTRIGGER PRINT PALLET KE PRINTER TSC TL241...")
        execute_physical_print_pallet(parsed_data)
    else:
        print("Error response:", res.text)
except Exception as e:
    print("Error:", e)
