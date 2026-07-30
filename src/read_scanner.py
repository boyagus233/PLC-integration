import serial
import time
import os
import json
import urllib.request
import urllib.error

# Konfigurasi Scanner
PORT_SCANNER = 'COM3' 
BAUD_RATE = 9600
API_URL = 'https://api.pms.yuasa.seavihive.com/api/fix-scanner'

# Fungsi untuk membaca LINE_NO dari file .env atau env variable
def get_line_no():
    # Coba baca dari file .env jika ada
    env_path = '.env'
    if os.path.exists(env_path):
        try:
            with open(env_path, 'r') as f:
                for line in f:
                    if line.strip() and not line.strip().startswith('#'):
                        key, val = line.strip().split('=', 1)
                        if key.strip() == 'LINE_NO':
                            return val.strip().strip('"').strip("'")
        except Exception:
            pass
            
    # Coba baca dari Environment Variable sistem, default ke "1"
    return os.environ.get('LINE_NO', '1')

LINE_NO = get_line_no()

print("=========================================")
print("  MONITOR & API INTEGRATION FOR SCANNER ")
print("=========================================")
print(f"[CONFIG] Line No    : {LINE_NO}")
print(f"[CONFIG] Scanner Port: {PORT_SCANNER}")
print(f"[CONFIG] API Target : {API_URL}")
print("=========================================")

def send_to_api(pack_code):
    payload = {
        "line_no": str(LINE_NO),
        "pack_code": pack_code
    }
    
    req_data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        API_URL, 
        data=req_data, 
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"\n[API] Mengirim data: {payload} ...")
    
    try:
        start_time = time.time()
        with urllib.request.urlopen(req, timeout=10) as response:
            res_status = response.status
            res_body = response.read().decode('utf-8')
            duration = time.time() - start_time
            print(f"[API] Sukses (Status: {res_status}) dalam {duration:.2f}s")
            print(f"[API] Respon: {res_body}")
    except urllib.error.HTTPError as e:
        res_body = e.read().decode('utf-8') if e.fp else ""
        print(f"[API ERROR] HTTP Error {e.code}: {e.reason}")
        if res_body:
            print(f"[API ERROR] Respon Server: {res_body}")
    except urllib.error.URLError as e:
        print(f"[API ERROR] Gagal menghubungi server: {e.reason}")
    except Exception as e:
        print(f"[API ERROR] Error tidak dikenal: {e}")

try:
    with serial.Serial(PORT_SCANNER, BAUD_RATE, timeout=1) as ser:
        print(f"\n[INFO] Terhubung ke {PORT_SCANNER}. Silakan scan barcode/QR code...")
        
        while True:
            if ser.in_waiting > 0:
                # Membaca data baris hasil scan
                barcode_raw = ser.readline()
                barcode_text = barcode_raw.decode('utf-8').strip()
                
                if barcode_text:
                    print(f"\n[SCAN TERDETEKSI] - Waktu: {time.strftime('%H:%M:%S')}")
                    print(f"Hasil Scan: {barcode_text}")
                    
                    # Kirim ke API
                    send_to_api(barcode_text)
                    
            time.sleep(0.05)
            
except serial.SerialException as e:
    print(f"[ERROR] Tidak dapat membuka {PORT_SCANNER}.")
    print(f"Detail Error: {e}")
    print("Pastikan port sudah benar dan tidak sedang digunakan oleh aplikasi lain.")
except KeyboardInterrupt:
    print("\nProgram dihentikan oleh pengguna.")
