import serial

COM_PORT = 'COM9'  # Jangan lupa sesuaikan dengan COM Port Anda!
BAUD_RATE = 9600

import time

def send_beep(scanner, beep_code):
    # WAKEUP: Kirim byte kosong untuk membangunkan scanner dari mode sleep
    scanner.write(b'\x00')
    time.sleep(0.1) # Tunggu 100ms agar scanner siap menerima perintah
    
    packet = [0x05, 0xE6, 0x04, 0x00, beep_code]
    checksum = (~sum(packet) + 1) & 0xFFFF
    packet.append((checksum >> 8) & 0xFF)
    packet.append(checksum & 0xFF)
    scanner.write(bytes(packet))

def send_led(scanner, led_code, state_on=True):
    # WAKEUP
    scanner.write(b'\x00')
    time.sleep(0.1)
    
    opcode = 0xE7 if state_on else 0xE8
    packet = [0x05, opcode, 0x04, 0x00, led_code]
    checksum = (~sum(packet) + 1) & 0xFFFF
    packet.append((checksum >> 8) & 0xFF)
    packet.append(checksum & 0xFF)
    scanner.write(bytes(packet))

def main():
    # Daftar lengkap (Full List) dalam bentuk List of Tuples agar ada nomor urut
    daftar_suara = [
        # PENDEK TINGGI (1-5)
        ("1 Pendek Tinggi (Default)", 0x00), ("2 Pendek Tinggi", 0x01), 
        ("3 Pendek Tinggi", 0x02), ("4 Pendek Tinggi", 0x03), ("5 Pendek Tinggi", 0x04),
        
        # PENDEK RENDAH (6-10)
        ("1 Pendek Rendah", 0x05), ("2 Pendek Rendah", 0x06), 
        ("3 Pendek Rendah", 0x07), ("4 Pendek Rendah", 0x08), ("5 Pendek Rendah", 0x09),
        
        # PANJANG TINGGI (11-15)
        ("1 Panjang Tinggi (Teeet)", 0x0A), ("2 Panjang Tinggi", 0x0B), 
        ("3 Panjang Tinggi", 0x0C), ("4 Panjang Tinggi", 0x0D), ("5 Panjang Tinggi", 0x0E),
        
        # PANJANG RENDAH (16-20)
        ("1 Panjang Rendah (Toooot)", 0x0F), ("2 Panjang Rendah", 0x10), 
        ("3 Panjang Rendah", 0x11), ("4 Panjang Rendah", 0x12), ("5 Panjang Rendah", 0x13),
        
        # UNIK / KOMBINASI (21-27)
        ("Fast Warble (Alarm Cepat)", 0x14),
        ("Slow Warble (Alarm Lambat)", 0x15),
        ("High-Low (Ti-Tot)", 0x16),
        ("Low-High (Tot-Ti)", 0x17),
        ("High-Low-High (Ti-Tot-Ti)", 0x18),
        ("Low-High-Low (Tot-Ti-Tot)", 0x19),
        ("High-High-Low-Low (Ti-Ti-Tot-Tot)", 0x1A)
    ]

    try:
        scanner = serial.Serial(COM_PORT, BAUD_RATE, timeout=1)
        print(f"[*] Terhubung ke {COM_PORT} - Scanner Siap!\n")
        
        while True:
            print("\n" + "="*40)
            print("      PILIH SUARA ZEBRA SCANNER")
            print("="*40)
            
            # Menampilkan menu
            for i, (nama, kode) in enumerate(daftar_suara, start=1):
                print(f"{i:2d}. {nama}")
                
            print("-" * 40)
            print(" 0. KELUAR")
            print("=" * 40)
            
            # Meminta input dari pengguna
            pilihan = input("\nMasukkan nomor suara yang ingin di-play (0-27): ")
            
            if pilihan == '0':
                print("[*] Keluar dari program. Sampai jumpa!")
                break
                
            if pilihan.isdigit():
                idx = int(pilihan)
                if 1 <= idx <= len(daftar_suara):
                    nama_suara, kode_suara = daftar_suara[idx-1]
                    print(f"\n[>] Memutar: {nama_suara} [Hex Code: {hex(kode_suara)}]")
                    
                    if idx == 22:
                        print("    [!] Menyalakan lampu MERAH...")
                        send_led(scanner, 0x02, state_on=True) # 0x02 = Red LED
                    
                    # Kirim perintah suara ke scanner
                    send_beep(scanner, kode_suara)
                    
                    if idx == 22:
                        time.sleep(2) # Tunggu 2 detik sampai bunyi slow warble selesai
                        print("    [!] Mematikan lampu MERAH...")
                        send_led(scanner, 0x02, state_on=False)
                else:
                    print("\n[!] Angka tidak ada di daftar. Pilih antara 1 sampai 27.")
            else:
                print("\n[!] Input tidak valid. Harap masukkan angka.")
                
    except Exception as e:
        print(f"\n[!] Terjadi Error pada koneksi: {e}")
        print("Pastikan COM_PORT benar dan tidak sedang digunakan oleh aplikasi lain.")
    finally:
        if 'scanner' in locals() and scanner.is_open:
            scanner.close()

if __name__ == '__main__':
    main()