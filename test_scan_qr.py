import requests
import json
import urllib3
from datetime import datetime

# Nonaktifkan warning SSL jika verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Konfigurasi Target API
SCANNER_URL = "https://api.pms.yuasa.seavihive.com/api/fix-scanner"
VALIDATE_URL = "https://api.pms.yuasa.seavihive.com/api/fix-scanner-masterbox-validate"
API_KEY = "Yu4saB4tterYindonesi4"
LINE_NO = "14"

# Default contoh barcode baterai
DEFAULT_QR = "YBID2609M17A0023A"

def main():
    print("=" * 65)
    print("  SIMULATOR SCAN QR BATERAI (PENGGANTI SCANNER FISIK)")
    print("  Mendukung Mode Normal & Mode Langsung Pallet (WIP)")
    print("=" * 65)
    print(f"Line No        : {LINE_NO}")
    print(f"Scanner 1 API  : {SCANNER_URL}")
    print(f"Scanner 2 API  : {VALIDATE_URL} (Validasi Pallet/WIP)")
    print("=" * 65)
    print("PILIHAN MODE:")
    print(" [1] Mode Pallet WIP (Scan + Validasi agar langsung siap cetak Pallet)")
    print(" [2] Mode Normal (Hanya Scan QR Scanner 1)")
    print("-" * 65)

    mode_choice = input("Pilih Mode [1/2] (default: 1): ").strip()
    is_wip_mode = (mode_choice != "2")

    print("\n" + "=" * 65)
    if is_wip_mode:
        print("  --> MODE AKTIF: [1] SCAN + VALIDASI PALLET WIP")
        print("      (Setiap scan akan otomatis ditandai siap masuk Pallet WIP)")
    else:
        print("  --> MODE AKTIF: [2] NORMAL SCANNER 1 ONLY")
    print("=" * 65)
    print("Instruksi:")
    print(" - Masukkan / Paste Kode QR Baterai lalu tekan [ENTER]")
    print(f" - Atau langsung tekan [ENTER] tanpa ketik untuk pakai default: '{DEFAULT_QR}'")
    print(" - Ketik 'q' lalu [ENTER] untuk keluar")
    print("=" * 65)

    count = 0

    while True:
        try:
            prompt_text = f"\n[Scan #{count + 1}] Masukkan Kode QR: "
            user_input = input(prompt_text).strip()

            if user_input.lower() in ['q', 'exit', 'quit']:
                print("\nKeluar dari simulator Scanner QR. Selesai!")
                break

            qr_code = user_input if user_input else DEFAULT_QR
            count += 1

            payload = {
                "line_no": str(LINE_NO),
                "pack_code": qr_code
            }

            headers = {
                "Content-Type": "application/json",
                "X-Scanner-Api-Key": API_KEY
            }

            # 1. Kirim ke Scanner 1 (/api/fix-scanner)
            print(f"\n[1/2] Mengirim ke Scanner 1 ({SCANNER_URL})...")
            res_scan = requests.post(SCANNER_URL, json=payload, headers=headers, timeout=10, verify=False)
            print(f"      Status: {res_scan.status_code} | Body: {res_scan.text[:120]}")

            if res_scan.status_code not in [200, 201]:
                print(f"--> [WARNING] Scanner 1 mengembalikan status {res_scan.status_code}")
                continue

            # 2. Jika mode WIP aktif, kirim ke Scanner 2 (/api/fix-scanner-masterbox-validate)
            if is_wip_mode:
                print(f"[2/2] Validasi Pallet/WIP ({VALIDATE_URL})...")
                res_val = requests.post(VALIDATE_URL, json=payload, headers=headers, timeout=10, verify=False)
                print(f"      Status: {res_val.status_code} | Body: {res_val.text[:120]}")

                if res_val.status_code in [200, 201]:
                    print(f"\n✅ [SUKSES] QR '{qr_code}' berhasil di-scan & SIAP masuk Pallet WIP!")
                else:
                    print(f"\n⚠ [WARNING] Validasi gagal ({res_val.status_code}): {res_val.text}")
            else:
                print(f"\n✅ [SUKSES] QR '{qr_code}' berhasil di-scan (Scanner 1 OK)!")

        except (KeyboardInterrupt, EOFError):
            print("\nProgram dihentikan oleh user.")
            break
        except Exception as e:
            print(f"\n[ERROR] Terjadi kesalahan: {e}")

if __name__ == "__main__":
    main()
