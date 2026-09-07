import requests
import json
import urllib3
from datetime import datetime

# Nonaktifkan warning SSL jika verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Konfigurasi Target API
API_URL = "https://api.pms.yuasa.seavihive.com/api/fix-scanner-counter-plc-gate"
API_KEY = "Yu4saB4tterYindonesi4"
LINE_NO = "13"
TAG_NAME = "_IO_EM_DI_02"

def main():
    print("=" * 60)
    print("  SIMULATOR COUNTER BATERAI NON-QR / CONVEYOR (TEST TOOL)")
    print("=" * 60)
    print(f"Target API : {API_URL}")
    print(f"Line No    : {LINE_NO}")
    print(f"Tag Name   : {TAG_NAME}")
    print("=" * 60)
    print("Instruksi:")
    print(" - Tekan [ENTER] untuk menaikkan counter (+1) & kirim ke API")
    print(" - Ketik 'r' lalu [ENTER] untuk mereset counter ke 0")
    print(" - Ketik 'q' lalu [ENTER] untuk keluar")
    print("=" * 60)

    counter = 0

    while True:
        try:
            user_input = input(f"\n[Counter Saat Ini: {counter}] Tekan ENTER (atau 'q' untuk keluar): ").strip().lower()
            if user_input in ['q', 'exit', 'quit']:
                print("\nKeluar dari simulator counter. Terima kasih!")
                break
            elif user_input == 'r':
                counter = 0
                print(">> Counter telah di-reset ke 0.")
                continue

            counter += 1
            timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            payload = {
                "line_no": str(LINE_NO),
                "counter": counter,
                "tag_name": TAG_NAME,
                "timestamp": timestamp_str
            }

            headers = {
                "Content-Type": "application/json",
                "X-Scanner-Api-Key": API_KEY
            }

            print(f"\n[SENDING...] Mengirim Counter #{counter}...")
            print(f"Payload JSON: {json.dumps(payload, indent=2)}")

            response = requests.post(API_URL, json=payload, headers=headers, timeout=5, verify=False)

            print(f"HTTP Status : {response.status_code}")
            print(f"Response    : {response.text}")

            if response.status_code in [200, 201]:
                print(f"🟢 SUKSES! Counter #{counter} berhasil dicatat di server backend.")
            else:
                print(f"🔴 WARNING! Server mengembalikan HTTP Status {response.status_code}.")

        except KeyboardInterrupt:
            print("\n\nKeluar dari simulator.")
            break
        except Exception as e:
            print(f"❌ Error Jaringan / System: {e}")

if __name__ == "__main__":
    main()
