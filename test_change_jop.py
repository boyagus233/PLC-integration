import requests
import json
import urllib3
from datetime import datetime

# Nonaktifkan warning SSL jika verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Konfigurasi Target API Change JOP
API_URL = "https://api.pms.yuasa.seavihive.com/api/fix-scanner-change-jop"
API_KEY = "Yu4saB4tterYindonesi4"
LINE_NO = "14"
PACK_CODE = "button_pressed"

def main():
    print("=" * 60)
    print("  SIMULATOR TOMBOL CHANGE JOB ORDER PRODUCTION (TEST TOOL)")
    print("=" * 60)
    print(f"Target API : {API_URL}")
    print(f"Line No    : {LINE_NO}")
    print(f"Pack Code  : {PACK_CODE}")
    print("=" * 60)
    print("Instruksi:")
    print(" - Tekan [ENTER] untuk simulasi tombol ditekan & kirim ke API")
    print(" - Ketik 'q' lalu [ENTER] untuk keluar")
    print("=" * 60)

    count = 0

    while True:
        try:
            user_input = input(f"\n[Tekan #{count}] Tekan ENTER untuk kirim (atau 'q' untuk keluar): ").strip().lower()
            if user_input in ['q', 'exit', 'quit']:
                print("\nKeluar dari simulator Change JOP. Terima kasih!")
                break

            count += 1
            timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            payload = {
                "line_no": str(LINE_NO),
                "pack_code": PACK_CODE
            }

            headers = {
                "Content-Type": "application/json",
                "X-Scanner-Api-Key": API_KEY
            }

            print(f"\n[SENDING...] Mengirim Request Ubah JOP #{count} ke {API_URL}...")
            print(f"Payload JSON: {json.dumps(payload, indent=2)}")

            response = requests.post(API_URL, json=payload, headers=headers, timeout=5, verify=False)

            print(f"\n[RESPONSE] HTTP Status Code : {response.status_code}")
            print(f"[RESPONSE] Response Body     : {response.text}")

            if response.status_code in [200, 201]:
                print(f"--> [SUKSES] Perubahan JOP berhasil diterima server! (Status {response.status_code})")
            else:
                print(f"--> [WARNING/GAGAL] Server mengembalikan status {response.status_code}")

        except KeyboardInterrupt:
            print("\nProgram dihentikan oleh user.")
            break
        except Exception as e:
            print(f"\n[ERROR] Gagal menghubungi API: {e}")

if __name__ == "__main__":
    main()
