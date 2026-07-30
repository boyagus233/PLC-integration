from pycomm3 import LogixDriver
from datetime import datetime
import time
import sys
import os

# ===== SETTING =====
PLC_IP = "192.168.1.20/1"
LINE_NO = 14  # Hardcode Line Number

tags = [
    "Recent_Weight",
    "Product_Weight",
    "Recent_Qty",
    "Product_Qty",
    "Recent_Quality",
    "Product_Type",
    "Product_Code1",
    "Product_Code2",
    "Product_Finishing",
    "Totalizer_Box"
]

# ===== PATH SETUP =====
script_dir = os.path.dirname(os.path.abspath(__file__))
log_dir = os.path.join(script_dir, "logs")
error_dir = os.path.join(script_dir, "error_log")

os.makedirs(log_dir, exist_ok=True)
os.makedirs(error_dir, exist_ok=True)

# ===== STATE =====
last_box = None
my_counter = 0

# ===== COLOR =====
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"

def status_line(msg, color=RESET):
    sys.stdout.write("\r" + color + msg + RESET + " " * 30)
    sys.stdout.flush()

def log_error(msg):
    filename = os.path.join(error_dir, "error_log.txt")
    with open(filename, "a") as f:
        f.write(f"{datetime.now()} - {msg}\n")

# ===== MAIN LOOP (TIDAK BOLEH MATI) =====
while True:
    try:
        status_line("[PLC] Connecting...", YELLOW)

        try:
            plc = LogixDriver(PLC_IP)
            plc.open()
        except Exception as e:
            # 🔌 CONNECT ERROR = RUNTIME (retry terus)
            log_error(f"RUNTIME ERROR (CONNECT): {str(e)}")
            status_line("[PLC] Cannot connect... retrying...", RED)
            time.sleep(2)
            continue

        status_line("[PLC] Connected ✓", GREEN)
        last_box = None

        # ===== READ LOOP =====
        while True:
            try:
                # ===== BACA DATA DARI PLC =====
                results = plc.read(*tags)

                if results is None:
                    raise RuntimeError("No data returned from PLC")

                current_values = {r.tag: r.value for r in results}

                if "Totalizer_Box" not in current_values:
                    raise RuntimeError("Tag Totalizer_Box missing")

                current_box = current_values["Totalizer_Box"]

                # ===== NO NEW DATA =====
                # Jika data belum berubah (belum ada box baru), diam dan tunggu
                if last_box is not None and current_box == last_box:
                    for i in range(3):
                        status_line(f"[DATA] Waiting" + "." * (i + 1), CYAN)
                        time.sleep(0.3)
                    continue

                # ==========================================
                # ===== NEW DATA DETECTED (MULAI CATAT) ====
                # ==========================================
                print("\r" + " " * 80, end="\r") # Clear loading bar

                now = datetime.now()
                time_short = now.strftime("%H:%M")
                time_full = now.strftime("%d%m%Y %H:%M:%S")
                
                # Format Timestamp untuk nama file: DDMMYYYY_HHMMSS
                # Contoh hasil: log_line_no_1_15072026_114357.txt
                timestamp_file = now.strftime("%d%m%Y_%H%M%S")
                filename = os.path.join(
                    log_dir,
                    f"log_line_no_{LINE_NO}_{timestamp_file}.txt"
                )

                if last_box is None:
                    my_counter += 1
                    print(f"{GREEN}[DATA] FIRST DATA #{my_counter}{RESET}")
                else:
                    my_counter += 1
                    print(f"{GREEN}[DATA] NEW BOX #{my_counter}{RESET}")

                last_box = current_box

                # ===== SUSUN LOGGING UNTUK PRINT & FILE =====
                lines = []

                # Masukkan ID dan Line No
                line_id = f"ID: {my_counter}"
                line_no_str = f"Line_No : {LINE_NO}"
                
                print(line_id)
                print(line_no_str)
                lines.append(line_id)
                lines.append(line_no_str)

                # Masukkan semua tag PLC
                for r in results:
                    line = f"{r.tag}: {r.value} ({r.type})"
                    print(line)
                    lines.append(line)

                # Masukkan Waktu
                line_time = f"Time: {time_short}"
                line_full_str = f"Timestamp: {time_full}"

                print(line_time)
                print(line_full_str)
                print("-" * 40)

                lines.append(line_time)
                lines.append(line_full_str)
                lines.append("-" * 40)

                # ===== SAVE LOG KE FILE BARU =====
                # Pakai "w" (write) karena setiap file pasti baru
                with open(filename, "w") as f:
                    for l in lines:
                        f.write(l + "\n")

                time.sleep(0.2)

            except (RuntimeError, OSError) as e:
                # 🔁 PLC / NETWORK ERROR
                log_error(f"RUNTIME ERROR: {str(e)}")
                status_line("[PLC] Disconnected... reconnecting...", RED)

                try:
                    plc.close()
                except:
                    pass

                time.sleep(1)
                break  # reconnect (kembali ke luar untuk connect PLC lagi)

            except Exception as e:
                # 💀 BENAR-BENAR CRASH
                log_error(f"FATAL ERROR: {str(e)}")
                status_line("[APP] Fatal error... restarting...", RED)

                try:
                    plc.close()
                except:
                    pass

                time.sleep(2)
                sys.exit(1)

    except Exception as e:
        # 💀 PROTEKSI TERAKHIR
        log_error(f"FATAL ERROR (OUTER): {str(e)}")
        status_line("[APP] Critical failure... restarting...", RED)
        time.sleep(2)
        sys.exit(1)