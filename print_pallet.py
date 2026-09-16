import requests
import json
import urllib3
from datetime import datetime

# Nonaktifkan warning SSL jika verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Konfigurasi Target API Pallet
API_URL = "https://api.pms.yuasa.seavihive.com/api/fix-scanner-pallet"
RETRY_API_URL = "https://api.pms.yuasa.seavihive.com/api/fix-scanner-pallet-retry"
API_KEY = "Yu4saB4tterYindonesi4"
LINE_NO = "14"
PRINTER_NAME = "TSC TL241"

try:
    import win32print
    HAS_PRINTER = True
except ImportError:
    HAS_PRINTER = False

def print_ke_tsc(data_dict):
    """Kirim perintah cetak fisik ke printer TSC TL241 jika terhubung"""
    if not HAS_PRINTER:
        return
    try:
        code = data_dict.get("code", "-")
        part_code = data_dict.get("part_code", "-")
        batt_type = data_dict.get("batt_type", "-")
        quantity = data_dict.get("quantity", "0")
        customer = data_dict.get("customer", "AFM (PT. SANTI YOGA)")
        order_no = data_dict.get("order_no", "-")
        prd_shift = data_dict.get("prd_shift", "-")
        code_production = data_dict.get("code_production", "-")

        tspl = f"""SIZE 70 mm, 50 mm
GAP 2 mm, 0 mm
DIRECTION 1
CLS
QRCODE 25,95,H,3,A,0,M2,S7,"{code}"
TEXT 160,95,"0",0,8,8,"{code}"
TEXT 160,123,"0",0,8,8,"Order No."
TEXT 250,123,"0",0,8,8,": {order_no}"
TEXT 160,151,"0",0,8,8,"Customer"
TEXT 250,151,"0",0,8,8,": {customer}"
TEXT 160,179,"0",0,8,8,"Part Code"
TEXT 250,179,"0",0,8,8,": {part_code}"
TEXT 25,210,"0",0,8,8,"Batt. Type"
TEXT 140,210,"0",0,8,8,": {batt_type}"
TEXT 25,238,"0",0,8,8,"Quantity"
TEXT 140,238,"0",0,8,8,": {quantity}"
TEXT 25,266,"0",0,8,8,"Prd/Shift/Mc"
TEXT 140,266,"0",0,8,8,": {prd_shift}"
TEXT 25,294,"0",0,8,8,"Kode Prod"
TEXT 140,294,"0",0,8,8,": {code_production}"
PRINT 1
"""
        hPrinter = win32print.OpenPrinter(PRINTER_NAME)
        try:
            hJob = win32print.StartDocPrinter(hPrinter, 1, ("Pallet Label", None, "RAW"))
            try:
                win32print.StartPagePrinter(hPrinter)
                win32print.WritePrinter(hPrinter, tspl.encode("utf-8"))
                win32print.EndPagePrinter(hPrinter)
                print(f"--> [PRINTER] Label fisik berhasil dikirim ke '{PRINTER_NAME}'!")
            finally:
                win32print.EndDocPrinter(hPrinter)
        finally:
            win32print.ClosePrinter(hPrinter)
    except Exception as e:
        print(f"--> [PRINTER INFO] Tidak mencetak ke '{PRINTER_NAME}': {e}")

def main():
    print("=" * 60)
    print("  SIMULATOR HIT API PRINT PALLET (TEST TOOL)")
    print("=" * 60)
    print(f"Target API : {API_URL}")
    print(f"Line No    : {LINE_NO}")
    print("=" * 60)
    print("Instruksi:")
    print(" - Tekan [ENTER]       : Hit API Cetak Pallet Baru")
    print(" - Ketik Kode Pallet   : Hit API Reprint Pallet (contoh: YBID.PLT...)")
    print(" - Ketik 'q'           : Keluar")
    print("=" * 60)

    count = 0

    while True:
        try:
            user_input = input(f"\n[Test #{count}] Tekan ENTER untuk kirim (atau 'q' untuk keluar): ").strip()
            if user_input.lower() in ['q', 'exit', 'quit']:
                print("\nKeluar dari simulator. Terima kasih!")
                break

            count += 1
            headers = {
                "Content-Type": "application/json",
                "X-Scanner-Api-Key": API_KEY
            }

            if user_input:
                target_url = RETRY_API_URL
                payload = {
                    "line_no": str(LINE_NO),
                    "pack_code": user_input
                }
                print(f"\n[SENDING...] Mengirim Request Reprint Pallet ke {target_url}...")
            else:
                target_url = API_URL
                payload = {
                    "line_no": str(LINE_NO)
                }
                print(f"\n[SENDING...] Mengirim Request Pallet Baru ke {target_url}...")

            print(f"Payload JSON: {json.dumps(payload, indent=2)}")

            response = requests.post(target_url, json=payload, headers=headers, timeout=10, verify=False)

            print(f"\n[RESPONSE] HTTP Status Code : {response.status_code}")
            print(f"[RESPONSE] Response Body     : {response.text}")

            if response.status_code in [200, 201]:
                print(f"--> [SUKSES] Pallet berhasil dibuat/diambil dari server! (Status {response.status_code})")
                try:
                    res_json = response.json()
                    data = res_json.get("data", {})
                    meta = data.get("metaData", {}) if isinstance(data, dict) else {}
                    pallet_data = {
                        "code": data.get("code", "-") if isinstance(data, dict) else "-",
                        "part_code": res_json.get("partCode") or meta.get("part_code") or "-",
                        "batt_type": meta.get("part_code") or res_json.get("partName") or "-",
                        "quantity": f"{data.get('quantityPcs', meta.get('quantity', 0))} pcs" if isinstance(data, dict) else "-",
                        "customer": meta.get("customer", "AFM (PT. SANTI YOGA)"),
                        "order_no": meta.get("order_no", "-"),
                        "prd_shift": meta.get("prodShiftMc", "-"),
                        "code_production": meta.get("codeProduction", "-")
                    }
                    print("\n--- DATA LABEL PALLET ---")
                    for k, v in pallet_data.items():
                        print(f"  {k:<16}: {v}")
                    print("-------------------------")
                    print_ke_tsc(pallet_data)
                except Exception as ex:
                    print(f"[NOTE] Parsing data: {ex}")
            elif response.status_code == 404:
                print("--> [INFO SERVER] Belum ada kardus/item yang siap di-pallet-kan di Line ini.")
            else:
                print(f"--> [WARNING/GAGAL] Server mengembalikan status {response.status_code}")

        except (KeyboardInterrupt, EOFError):
            print("\nProgram dihentikan.")
            break
        except Exception as e:
            print(f"\n[ERROR] Gagal menghubungi API: {e}")

if __name__ == "__main__":
    main()
