from pywinauto import Application
import time
import requests
import win32print
import sys
from datetime import datetime

# Konfigurasi
PRINTER_NAME = "TSC TL241"
API_URL = "https://api.pms.yuasa.seavihive.com/api/fix-scanner-pallet"
API_LINE_NO = "1"      # Payload API menggunakan "1" agar data item ditemukan di database
LABEL_LINE_NO = "01"   # Label stiker cetak menampilkan "01"
MONITOR_ADDRESS = "0.05"  # Alamat input tombol (MC6 / 0.05) yang dipantau

def print_qr_label(data_dict):
    """Mengirim perintah print (TSPL) dengan format QR Code dan Detail Label ke TSC TL241"""
    code = data_dict.get("code", "-")
    part_code = data_dict.get("part_code", "-")
    batt_type = data_dict.get("batt_type", "-")
    quantity = data_dict.get("quantity", "0")
    date_str = data_dict.get("date_str", "-")
    
    # Format TSPL untuk kertas 4cm x 3cm dengan QR Code & Detail Text
    tspl_command = f"""SIZE 40 mm, 30 mm
GAP 2 mm, 0 mm
DIRECTION 1
CLS
TEXT 20,10,"2",0,1,1,"PT. YUASA BATTERY INDONESIA"
BAR 20,28,280,2
QRCODE 15,45,M,3,A,0,"{code}"
TEXT 105,45,"1",0,1,1,"Group Code : {code}"
TEXT 105,65,"1",0,1,1,"Order No.  : -"
TEXT 105,85,"1",0,1,1,"Customer   : AFM (PT. SANTI YOGA)"
TEXT 105,105,"1",0,1,1,"Part Code  : {part_code}"
TEXT 105,125,"1",0,1,1,"Batt. Type : {batt_type}"
TEXT 105,145,"1",0,1,1,"Quantity   : {quantity} PCS"
TEXT 105,165,"1",0,1,1,"Prod/Shf/Mc: {date_str}/I/{LABEL_LINE_NO}"
PRINT 1
"""
    try:
        hPrinter = win32print.OpenPrinter(PRINTER_NAME)
        try:
            hJob = win32print.StartDocPrinter(hPrinter, 1, ("PLC Auto QR Label", None, "RAW"))
            try:
                win32print.StartPagePrinter(hPrinter)
                win32print.WritePrinter(hPrinter, tspl_command.encode('utf-8'))
                win32print.EndPagePrinter(hPrinter)
                print(f"[PRINTER] Sukses mencetak QR Label Pallet: {code}")
            finally:
                win32print.EndDocPrinter(hPrinter)
        finally:
            win32print.ClosePrinter(hPrinter)
    except Exception as e:
        print(f"[PRINTER ERROR] Gagal mengirim print job ke TSC: {e}")

def hit_api_pallet():
    """Mengirim request ke API dan memparsing hasilnya untuk kebutuhan cetak"""
    payload = {"line_no": API_LINE_NO}
    try:
        print(f"[API] Mengirim POST request untuk Line {API_LINE_NO}...")
        response = requests.post(API_URL, json=payload, timeout=5)
        if response.status_code == 200:
            res_data = response.json()
            data = res_data.get("data", {})
            metadata = data.get("metaData", {})
            
            # Parsing tanggal dari createdAt
            created_at_raw = data.get("createdAt", "")
            try:
                dt_part = created_at_raw.split(".")[0]
                dt = datetime.strptime(dt_part, "%Y-%m-%dT%H:%M:%S")
                date_str = dt.strftime("%d-%b-%Y")
            except:
                date_str = datetime.now().strftime("%d-%b-%Y")
                
            # Parsing Part Code & Battery Type dari metadata
            raw_part_code = metadata.get("part_code", "-")
            parts = [p.strip() for p in raw_part_code.split(" ") if p.strip()]
            if len(parts) >= 2:
                part_code = parts[0]
                # Menggabungkan sisa bagian untuk Battery Type
                batt_type = " ".join(parts[1:])
            else:
                part_code = raw_part_code
                batt_type = "-"
                
            parsed_data = {
                "code": data.get("code", "-"),
                "part_code": part_code,
                "batt_type": batt_type,
                "quantity": str(metadata.get("quantity", "0")),
                "date_str": date_str
            }
            
            print(f"[API] Sukses! Data Pallet diperoleh: {parsed_data['code']}")
            return parsed_data
        else:
            print(f"[API ERROR] HTTP Status Code: {response.status_code}")
            try:
                err_msg = response.json().get("message", "")
                print(f"[API ERROR MESSAGE] {err_msg}")
            except:
                pass
    except Exception as e:
        print(f"[API ERROR] Gagal hit API: {e}")
    return None

def main():
    print("==================================================")
    print("      PLC OMRON TO TSC PRINTER BRIDGE ACTIVE      ")
    print("==================================================")
    print("Metode: UI Automation (pywinauto) via Watch Window")
    print(f"Monitoring PLC Address: {MONITOR_ADDRESS}")
    print(f"Target Printer: {PRINTER_NAME} (Size: 4cm x 3cm)")
    print(f"API Line Payload: {API_LINE_NO} | Label Line: {LABEL_LINE_NO}")
    print("--------------------------------------------------")
    print("PASTIKAN RUN COMMAND PROMPT SEBAGAI ADMINISTRATOR!")
    print("--------------------------------------------------\n")

    try:
        print("Menghubungkan ke CX-Programmer...")
        app = Application(backend="win32").connect(title_re=".*CX-Programmer.*")
        main_window = app.window(title_re=".*CX-Programmer.*")
        
        print("Mencari Watch Window...")
        watch_window = main_window.child_window(title="Watch Window", class_name="AfxWnd42")
        list_view = watch_window.child_window(class_name="SysListView32", found_index=0)
        
        item_count = list_view.item_count()
        if item_count == 0:
            print("Error: Watch Window kosong! Harap tambahkan variabel ke Watch Window.")
            sys.exit(1)
            
        print(f"Sukses! Terhubung ke Watch Window dengan {item_count} variabel.")
        print("Menunggu tombol ditekan... Tekan Ctrl+C untuk berhenti.\n")
        
        last_state = "0"
        
        while True:
            try:
                item_count = list_view.item_count()
                target_row = -1
                
                # Cari baris yang memiliki alamat 0.05
                for row in range(item_count):
                    address = list_view.get_item(row, 2).text().strip()
                    if address == MONITOR_ADDRESS:
                        target_row = row
                        break
                
                if target_row == -1:
                    time.sleep(1.0)
                    continue
                    
                # Kolom ke-5 (index 5) di Watch Window adalah kolom 'Value'
                current_state = list_view.get_item(target_row, 5).text().strip()
                
                # Deteksi transisi dari '0' ke '1'
                if current_state == "1" and last_state == "0":
                    print(f"\n[PLC EVENT] Tombol {MONITOR_ADDRESS} DITEKAN! (Value: {current_state})")
                    
                    # 1. Hit API
                    pallet_data = hit_api_pallet()
                    
                    # 2. Print QR Label jika data sukses diperoleh
                    if pallet_data:
                        print_qr_label(pallet_data)
                    else:
                        print("[SYSTEM] Batal cetak karena gagal mengambil data dari API.")
                        
                last_state = current_state
            except Exception as e:
                # Abaikan jika ada kegagalan sesaat membaca UI
                pass
                
            time.sleep(0.1) # Cek setiap 100ms
            
    except KeyboardInterrupt:
        print("\nProgram dihentikan oleh user.")
    except Exception as e:
        print(f"\nGagal menghubungkan ke CX-Programmer: {e}")
        print("Harap pastikan:")
        print("1. Software CX-Programmer sedang aktif dan menampilkan Watch Window.")
        print("2. Program Python ini dijalankan sebagai ADMINISTRATOR.")

if __name__ == "__main__":
    main()
