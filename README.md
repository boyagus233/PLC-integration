# Dokumentasi Jembatan Otomasi Yuasa (Scanner & PLC Bridge)

Proyek ini adalah aplikasi jembatan (*bridge*) terpadu untuk stasiun POS produksi di **PT. YUASA BATTERY INDONESIA**. Aplikasi ini mengintegrasikan barcode/QR scanner serial, pembacaan downtime mesin PLC Omron CP2E, dan pemicu tombol cetak otomatis label QR Pallet seukuran 4x3 cm ke printer thermal TSC TL241.

---

## 📂 Struktur Direktori Kerja (`D:\PLC`)

Untuk mempermudah pemeliharaan (*maintenance*), folder proyek telah dirapikan dengan struktur berikut:

```text
D:\PLC\
├── Yuasa_Scanner_App.exe        # Aplikasi GUI utama (Kompilasi EXE)
├── config.ini                   # File konfigurasi utama POS (sangat krusial untuk setup lapangan)
├── Mulai_Jembatan_Timbangan.bat    # Pintasan script batch administrator untuk monitoring downtime timbangan
├── README.md                    # Dokumentasi teknis proyek (berkas ini)
├── logs/                        # Folder log pemeliharaan harian (dipisah per fungsi)
│   ├── scanner_YYYY-MM-DD.log   # Log aktivitas scan & API scanner
│   ├── downtime_YYYY-MM-DD.log  # Log aktivitas monitoring bit & API downtime
│   └── printer_YYYY-MM-DD.log   # Log cetak label, API pallet, & status driver printer
└── src/                         # Folder berisi source code mentah Python
    ├── read_scanner_gui.py      # Source code aplikasi terpadu GUI (Tkinter + Multithreading)
    ├── read_scanner.py          # Script scanner versi CLI lama (cadangan)
    ├── read_value.py            # Script downtime versi CLI lama (cadangan)
    └── plc_print_bridge.py      # Script printer bridge versi CLI lama (cadangan)
```

---

## ⚙️ Panduan Pengaturan `config.ini`

Ketika memasang aplikasi di komputer POS baru, Anda **hanya perlu menyesuaikan file ini**:

```ini
[SCANNER_CONFIG]
LINE_NO = 1                                               # Nomor line stasiun POS
PORT_SCANNER = COM10                                      # Port serial scanner Zebra di POS tersebut
BAUD_RATE = 9600                                          # Baud rate scanner (default 9600)
API_URL = https://api.pms.yuasa.seavihive.com/api/fix-scanner  # Endpoint API scan barcode

[DOWNTIME_CONFIG]
ENABLE = yes                                              # Nyalakan 'yes' atau matikan 'no' fitur downtime
API_URL = https://api.pms.yuasa.seavihive.com/api/fix-scanner-downtime # Endpoint API log downtime
DOWNTIME_LOG_FILENAME = downtime_log.txt                  # Nama file log lokal downtime
SAVE_LOCATION = desktop                                   # Menyimpan file di 'desktop' (dinamis) atau 'app_dir'

[PRINTER_CONFIG]
ENABLE = yes                                              # Nyalakan 'yes' atau matikan 'no' pemicu cetak tombol
PRINTER_NAME = TSC TL241                                  # Nama driver printer TSC yang terinstal di Windows
API_URL = https://api.pms.yuasa.seavihive.com/api/fix-scanner-pallet # Endpoint API pallet Yuasa
MONITOR_ADDRESS = 0.05                                    # Alamat bit tombol fisik di Watch Window
API_LINE_NO = 1                                           # Payload Line untuk pencarian database API
LABEL_LINE_NO = 01                                        # Line yang akan tercetak di stiker kertas label
LABEL_WIDTH = 75                                          # Lebar kertas stiker dalam mm (contoh: 75)
LABEL_HEIGHT = 100                                        # Tinggi kertas stiker dalam mm (contoh: 100)
LABEL_GAP = 2                                             # Gap antar kertas stiker dalam mm (default: 2)
LABEL_ORIENTATION = landscape                             # Orientasi cetak: 'portrait' atau 'landscape'
```

---

## 🛠️ Persyaratan Lingkungan Pengembang (Developer Setup)

Jika tim developer ingin mengedit source code di dalam folder `src/`, pastikan library berikut sudah terinstal di environment Python (rekomendasi Python 3.10+):

```bash
pip install pyserial requests pywinauto pywin32
```

### Langkah Kompilasi Ulang ke Executable (`.exe`)
Apabila developer melakukan perubahan kode pada `src/read_scanner_gui.py` dan ingin mengemas ulang menjadi `.exe` baru:
1.  Buka **Command Prompt / PowerShell** di direktori `D:\PLC`.
2.  Jalankan perintah PyInstaller berikut:
    ```bash
    python -m PyInstaller --onefile --windowed --name="Yuasa_Scanner_App" d:\PLC\src\read_scanner_gui.py
    ```
3.  Pindahkan file output `Yuasa_Scanner_App.exe` dari folder `dist/` ke root `D:\PLC\`.
4.  Hapus folder sementara `build/`, `dist/`, dan file `Yuasa_Scanner_App.spec` agar direktori tetap rapi.

---

## 📌 Alur Kerja Sistem (System Workflow)

```mermaid
graph TD
    A[Aplikasi Utama Terpadu] --> B(Thread 1: Scanner serial)
    A --> C(Thread 2: Loop PLC Terpadu)
    
    B -->|Membaca COM Port| B1(Data scan masuk)
    B1 -->|POST API| B2[/api/fix-scanner]
    B2 --> B3[(Log: scanner_YYYY-MM-DD.log)]
    
    C -->|Membaca Watch Window| C1{Pengecekan Aktif}
    
    C1 -->|1. Downtime Enable| D1(Deteksi Perubahan Bit Mesin)
    D1 -->|POST API| D3[/api/fix-scanner-downtime]
    D3 --> D4[(Log: downtime_YYYY-MM-DD.log)]
    
    C1 -->|2. Printer Enable| E1(Deteksi Tombol 0.05 Transisi 0 -> 1)
    E1 -->|POST API Pallet| E2[/api/fix-scanner-pallet]
    E2 -->|Respons 200 OK| E3(Kirim format TSPL via win32print)
    E3 -->|Cetak Label 4x3 cm| E4[Printer TSC TL241]
    E1 --> E5[(Log: printer_YYYY-MM-DD.log)]
```
