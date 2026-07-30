from pywinauto import Application
import time
import os
import sys
import requests

# ==========================================
# KONFIGURASI
# ==========================================
LINE_NO = "1"  # Nomor Line untuk station ini
API_URL = "https://api.pms.yuasa.seavihive.com/api/fix-scanner-downtime"

print("Connecting to CX-Programmer...")
try:
    app = Application(backend="win32").connect(title_re=".*CX-Programmer.*")
    main_window = app.window(title_re=".*CX-Programmer.*")
    
    print("Locating Watch Window...")
    watch_window = main_window.child_window(title="Watch Window", class_name="AfxWnd42")
    list_view = watch_window.child_window(class_name="SysListView32", found_index=0)
    
    item_count = list_view.item_count()
    if item_count == 0:
        print("Error: Watch Window kosong!")
        sys.exit(1)
        
    print(f"Jembatan Downtime Aktif! Mendeteksi {item_count} baris data.")
    log_path = "C:\\Users\\yamada\\Desktop\\downtime_log.txt"
    realtime_path = "C:\\Users\\yamada\\Desktop\\timbangan_data.txt"
    
    last_values = {}
    
    # Inisialisasi cache
    for row in range(item_count):
        try:
            plc_name = list_view.get_item(row, 0).text().strip()
            symbol_name = list_view.get_item(row, 1).text().strip()
            address = list_view.get_item(row, 2).text().strip()
            value = list_view.get_item(row, 5).text().strip()
            comment = list_view.get_item(row, 7).text().strip()
            
            key = (plc_name, symbol_name, address)
            last_values[key] = value
        except:
            pass
            
    print("Mulai memantau perubahan data. Tekan Ctrl+C untuk berhenti.\n")
    
    while True:
        try:
            item_count = list_view.item_count()
            
            # Update nilai realtime A1 Excel
            if item_count > 0:
                first_val = list_view.get_item(0, 5).text().strip()
                with open(realtime_path, "w", encoding="utf-8") as f:
                    f.write(first_val)
            
            # Pindai seluruh baris mesin di Watch Window
            for row in range(item_count):
                plc_name = list_view.get_item(row, 0).text().strip()
                symbol_name = list_view.get_item(row, 1).text().strip()
                address = list_view.get_item(row, 2).text().strip()
                value = list_view.get_item(row, 5).text().strip()
                comment = list_view.get_item(row, 7).text().strip()
                
                key = (plc_name, symbol_name, address)
                
                # Jika ada perubahan nilai (downtime terdeteksi)
                if key not in last_values or last_values[key] != value:
                    status = "RUNNING" if value == "1" else "STOPPED"
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                    
                    # 1. Catat ke file TXT Lokal
                    log_line = f"[{timestamp}] PLC: {plc_name} | Symbol: {symbol_name} | Address: {address} | Status: {status} | Comment: {comment}\n"
                    try:
                        with open(log_path, "a", encoding="utf-8") as f:
                            f.write(log_line)
                    except Exception as e_local:
                        print(f"[{timestamp}] Gagal menulis log lokal: {e_local}")
                    
                    print(f"[{timestamp}] {symbol_name} ({comment}) -> {status}")
                    
                    # 2. Kirim Data POST ke API Yuasa Anda
                    payload = {
                        "line_no": LINE_NO,
                        "code_machine": symbol_name,
                        "address": address,
                        "status": status,
                        "comment": comment,
                        "timestamp_plc": timestamp
                    }
                    
                    try:
                        headers = {"Content-Type": "application/json"}
                        response = requests.post(API_URL, json=payload, headers=headers, timeout=5)
                        
                        if response.status_code == 200:
                            print(f"  └─ ✅ API Sukses Terkirim: {response.text.strip()}")
                        else:
                            print(f"  └─ ❌ API Gagal (Status {response.status_code}): {response.text.strip()}")
                    except Exception as e_api:
                        print(f"  └─ ⚠️ API Eror Jaringan: {e_api}")
                        
                    last_values[key] = value
        except Exception as e:
            pass
            
        time.sleep(0.1)
        
except KeyboardInterrupt:
    print("\nJembatan Downtime dihentikan.")
except Exception as e:
    print("Error:", e)
