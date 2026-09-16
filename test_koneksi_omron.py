import serial
import time
import sys
import traceback

def calculate_fcs(cmd_str):
    fcs = 0
    for char in cmd_str:
        fcs ^= ord(char)
    return f"{fcs:02X}"

def main():
    print("="*50)
    print(" ALAT TES KONEKSI OMRON CP2E (SERIAL HOSTLINK)")
    print("="*50)
    
    port = input("Masukkan Port (Contoh: COM13) [Enter untuk COM13]: ").strip()
    if not port:
        port = "COM13"
        
    baud = 9600
    
    formats_to_test = [
        ("7,E,2 (Standard)", serial.SEVENBITS, serial.PARITY_EVEN, serial.STOPBITS_TWO),
        ("8,N,1 (Custom)", serial.EIGHTBITS, serial.PARITY_NONE, serial.STOPBITS_ONE)
    ]
    
    sukses = False

    for nama_format, bits, parity, stops in formats_to_test:
        print(f"\n[{nama_format}] Mencoba koneksi dengan format ini...")
        try:
            ser = serial.Serial(port=port, baudrate=baud, bytesize=bits, parity=parity, stopbits=stops, timeout=1.5)
            cmd_body = "@00RD00000001"
            frame = f"{cmd_body}{calculate_fcs(cmd_body)}*\r"
            ser.write(frame.encode('ascii'))
            time.sleep(0.5)
            response = ser.readline().decode('ascii', errors='ignore').strip()
            ser.close()
            
            if response:
                print(f" -> Balasan: '{response}'")
                if response.startswith("@00RD00"):
                    print(f"\n>> BINGO! KONEKSI SUKSES 100% PADA FORMAT: {nama_format}!")
                    sukses = True
                    break
                else:
                    print(" -> Balasan aneh / garbage (Bukan HostLink).")
            else:
                print(" -> Balasan: KOSONG (Timeout)")
                
        except Exception as e:
            print(f" -> ERROR: {e}")
            if "Access is denied" in str(e):
                print("\n>> KESIMPULAN: Port dipakai aplikasi lain! Tutup CX-Programmer/CX-Server!")
                break
                
    if not sukses:
        print("\n>> KESIMPULAN AKHIR: Semua percobaan GAGAL (Timeout/Kosong).")
        print("   Kemungkinan:")
        print("   1. PLC belum di-restart (cabut-colok listrik) setelah setting CX-Programmer.")
        print("   2. Settingan di CX-Programmer belum HostLink.")
        print("   3. Jumper RS (Pin 3) ke CS (Pin 4) kendor.")

    print("\n" + "="*50)
    input("Tekan Enter untuk menutup layar ini...")

if __name__ == "__main__":
    main()
