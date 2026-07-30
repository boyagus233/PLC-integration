import os
import sys
import time
import serial
import requests
import logging
import threading
import shutil
import configparser
import socket
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess

# PyWin32 and PyWinAuto imports
try:
    import win32print
    PYWIN32_AVAILABLE = True
except ImportError:
    PYWIN32_AVAILABLE = False

try:
    from pywinauto import Application
    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False

# Dynamic import for Timbangan Rockwell
try:
    from pycomm3 import LogixDriver
    PYCOMM3_AVAILABLE = True
except ImportError:
    PYCOMM3_AVAILABLE = False

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False

# --- SETUP DIREKTORI & LOGGING ---
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(SCRIPT_DIR).lower() == 'src':
        BASE_DIR = os.path.dirname(SCRIPT_DIR)
    else:
        BASE_DIR = SCRIPT_DIR

LOG_DIR = os.path.join(BASE_DIR, "logs")

# Sub-direktori log terpisah per kategori
LOG_DIR_SCANNER   = os.path.join(LOG_DIR, "scanner")
LOG_DIR_DOWNTIME  = os.path.join(LOG_DIR, "downtime")
LOG_DIR_PRINTER   = os.path.join(LOG_DIR, "printer")
LOG_DIR_TIMBANGAN = os.path.join(LOG_DIR, "timbangan")

for d in [LOG_DIR_SCANNER, LOG_DIR_DOWNTIME, LOG_DIR_PRINTER, LOG_DIR_TIMBANGAN]:
    os.makedirs(d, exist_ok=True)

# Subfolders untuk Masterbox Watcher (di dalam logs/timbangan/)
for folder in ["sent", "error", "failed"]:
    os.makedirs(os.path.join(LOG_DIR_TIMBANGAN, folder), exist_ok=True)

def setup_logger(name, log_file, level=logging.INFO):
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    handler = logging.FileHandler(log_file, encoding="utf-8")
    handler.setFormatter(formatter)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if logger.hasHandlers():
        logger.handlers.clear()
    logger.addHandler(handler)
    
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    
    return logger

# File log per subfolder
_today = datetime.now().strftime('%Y-%m-%d')
scanner_log_file   = os.path.join(LOG_DIR_SCANNER,   f"scanner_{_today}.log")
downtime_log_file  = os.path.join(LOG_DIR_DOWNTIME,  f"downtime_{_today}.log")
printer_log_file   = os.path.join(LOG_DIR_PRINTER,   f"printer_{_today}.log")
timbangan_log_file = os.path.join(LOG_DIR_TIMBANGAN, f"timbangan_{_today}.log")

# Inisialisasi logger terpisah
scanner_logger   = setup_logger("scanner_logger",   scanner_log_file)
downtime_logger  = setup_logger("downtime_logger",  downtime_log_file)
printer_logger   = setup_logger("printer_logger",   printer_log_file)
timbangan_logger = setup_logger("timbangan_logger", timbangan_log_file)

# Kelas Router Logging dinamis untuk membelah log secara otomatis
class CustomLogger:
    INFO = logging.INFO
    ERROR = logging.ERROR
    
    @staticmethod
    def info(msg):
        msg_str = str(msg)
        if "[SCANNER]" in msg_str:
            scanner_logger.info(msg_str)
        elif "[DOWNTIME]" in msg_str:
            downtime_logger.info(msg_str)
        elif "[PRINTER]" in msg_str:
            printer_logger.info(msg_str)
        elif "[TIMBANGAN]" in msg_str or "[MASTERBOX]" in msg_str:
            timbangan_logger.info(msg_str)
        else:
            scanner_logger.info(msg_str)
            downtime_logger.info(msg_str)
            printer_logger.info(msg_str)
            timbangan_logger.info(msg_str)

    @staticmethod
    def error(msg):
        msg_str = str(msg)
        if "[SCANNER]" in msg_str:
            scanner_logger.error(msg_str)
        elif "[DOWNTIME]" in msg_str:
            downtime_logger.error(msg_str)
        elif "[PRINTER]" in msg_str:
            printer_logger.error(msg_str)
        elif "[TIMBANGAN]" in msg_str or "[MASTERBOX]" in msg_str:
            timbangan_logger.error(msg_str)
        else:
            scanner_logger.error(msg_str)
            downtime_logger.error(msg_str)
            printer_logger.error(msg_str)
            timbangan_logger.error(msg_str)

logging = CustomLogger()

# --- UTILITY PEMROTOKOALAN OMRON FINS & HOST LINK ---
class OmronPLCHelper:
    @staticmethod
    def calculate_fcs(cmd_str):
        fcs = 0
        for char in cmd_str:
            fcs ^= ord(char)
        return f"{fcs:02X}"
        
    @staticmethod
    def read_words_serial(port_name, baud_rate, area_type, start_word, count):
        cmd_code = "RG" if area_type == "DM" else "RD"
        addr_str = f"{start_word:04d}"
        count_str = f"{count:04d}"
        cmd_body = f"@00{cmd_code}{addr_str}{count_str}"
        fcs = OmronPLCHelper.calculate_fcs(cmd_body)
        frame = f"{cmd_body}{fcs}*\r"
        
        try:
            ser = serial.Serial(port_name, baud_rate, parity=serial.PARITY_EVEN, bytesize=serial.SEVENBITS, stopbits=serial.STOPBITS_TWO, timeout=0.3)
            ser.write(frame.encode('ascii'))
            response = ser.readline().decode('ascii', errors='ignore').strip()
            ser.close()
            
            if response.startswith(f"@00{cmd_code}00"):
                data_part = response[7:-3] # potong header dan FCS
                words = []
                for i in range(0, len(data_part), 4):
                    if i + 4 <= len(data_part):
                        words.append(int(data_part[i:i+4], 16))
                return words
        except Exception:
            pass
        return None

    @staticmethod
    def read_words_fins_udp(ip_address, port, area_type, start_word, count):
        # DM Area = 0x82, CIO Words Area = 0xB0 (CJ/CP series) atau 0x30/0x80
        area_code = 0x82 if area_type == "DM" else 0xB0
        
        addr_bytes = bytearray([
            (start_word >> 16) & 0xFF,
            (start_word >> 8) & 0xFF,
            start_word & 0xFF,
            0x00 # Bit position 0
        ])
        
        header = bytearray([
            0x80, 0x00, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
        ])
        command = bytearray([0x01, 0x01]) # Command Read
        params = bytearray([area_code]) + addr_bytes + bytearray([(count >> 8) & 0xFF, count & 0xFF])
        packet = header + command + params
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(0.5)
            sock.sendto(packet, (ip_address, port))
            data, addr = sock.recvfrom(1024)
            sock.close()
            
            if len(data) >= 14:
                end_code = data[12:14]
                if end_code == b'\x00\x00': # FINS Success
                    raw_data = data[14:]
                    words = []
                    for i in range(0, len(raw_data), 2):
                        if i + 1 < len(raw_data):
                            words.append(int.from_bytes(raw_data[i:i+2], byteorder='big'))
                    return words
        except Exception:
            pass
        return None

def parse_omron_address(addr_str):
    """
    Mengubah alamat text (e.g., '0.05', 'D100') ke format terstruktur.
    Returns: (area_type, word_address, bit_index)
    """
    addr_str = addr_str.strip().upper()
    if addr_str.startswith("D"):
        body = addr_str[1:]
        if "." in body:
            parts = body.split(".")
            return "DM", int(parts[0]), int(parts[1])
        else:
            return "DM", int(body), None
    elif "." in addr_str:
        parts = addr_str.split(".")
        try:
            return "CIO", int(parts[0]), int(parts[1])
        except ValueError:
            return None, None, None
    else:
        try:
            return "CIO", int(addr_str), None
        except ValueError:
            return None, None, None

def words_to_ascii(word_list):
    """Mengubah list word data memori PLC ke ASCII String"""
    chars = []
    for w in word_list:
        char1 = (w >> 8) & 0xFF
        char2 = w & 0xFF
        if char1 != 0: chars.append(chr(char1))
        if char2 != 0: chars.append(chr(char2))
    return "".join(chars).strip()


# --- LOAD KONFIGURASI config.ini ---
CONFIG_FILE = os.path.join(BASE_DIR, "config.ini")

def load_config():
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_FILE):
        logging.info("config.ini tidak ditemukan. Membuat config.ini default...")
        config["SCANNER_CONFIG"] = {
            "LINE_NO": "1",
            "PORT_SCANNER": "COM3",
            "BAUD_RATE": "9600",
            "API_URL": "https://api.pms.yuasa.seavihive.com/api/fix-scanner"
        }
        config["DOWNTIME_CONFIG"] = {
            "ENABLE": "yes",
            "API_URL": "https://api.pms.yuasa.seavihive.com/api/fix-scanner-downtime",
            "DOWNTIME_LOG_FILENAME": "downtime_log.txt",
            "SAVE_LOCATION": "desktop",
            "CONNECTION_MODE": "cx_programmer",
            "PLC_IP": "192.168.1.10",
            "PLC_PORT": "COM5",
            "PLC_BAUD": "9600",
            "DOWNTIME_ADDRESSES": "MC1:10.01:Mesin 1, MC2:10.02:Mesin 2, MC3:10.03:Mesin 3, MC4:10.04:Mesin 4, MC5:10.05:Mesin 5, MC6:10.06:Mesin 6"
        }
        config["PRINTER_CONFIG"] = {
            "ENABLE": "yes",
            "PRINTER_NAME": "TSC TL241",
            "API_URL": "https://api.pms.yuasa.seavihive.com/api/fix-scanner-pallet",
            "RETRY_API_URL": "https://api.pms.yuasa.seavihive.com/api/fix-scanner-pallet-retry",
            "MONITOR_ADDRESS": "0.05",
            "API_LINE_NO": "1",
            "LABEL_LINE_NO": "01",
            "LABEL_WIDTH": "40",
            "LABEL_HEIGHT": "30",
            "LABEL_GAP": "2",
            "LABEL_ORIENTATION": "portrait"
        }
        config["TIMBANGAN_CONFIG"] = {
            "ENABLE": "yes",
            "LINE_NO": "14",
            "API_URL": "https://api.pms.yuasa.seavihive.com/api/fix-scanner-masterbox",
            "RETRY_API_URL": "https://api.pms.yuasa.seavihive.com/api/fix-scanner-masterbox-retry",
            "LABEL_WIDTH": "75",
            "LABEL_HEIGHT": "100",
            "LABEL_GAP": "2",
            "LABEL_ORIENTATION": "landscape",
            "CONNECTION_MODE": "rockwell",
            "PLC_IP": "192.168.1.20/1",
            "PLC_PORT": "COM6",
            "PLC_BAUD": "9600",
            "TAG_WEIGHT": "Recent_Weight",
            "TAG_QTY": "Recent_Qty",
            "TAG_TYPE": "Product_Type",
            "TAG_TOTALIZER": "Totalizer_Box"
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                config.write(f)
            logging.info("config.ini default berhasil dibuat.")
        except Exception as e:
            logging.error(f"Gagal membuat config.ini default: {e}")
    else:
        try:
            config.read(CONFIG_FILE)
            logging.info("config.ini berhasil dimuat.")
        except Exception as e:
            logging.error(f"Gagal membaca config.ini: {e}")
    
    # Ambil nilai Scanner
    scanner_enable = config.getboolean("SCANNER_CONFIG", "ENABLE", fallback=True)
    line_no = config.get("SCANNER_CONFIG", "LINE_NO", fallback="1")
    scanner_port = config.get("SCANNER_CONFIG", "PORT_SCANNER", fallback="COM3")
    scanner_baud = config.getint("SCANNER_CONFIG", "BAUD_RATE", fallback=9600)
    scanner_url = config.get("SCANNER_CONFIG", "API_URL", fallback="https://api.pms.yuasa.seavihive.com/api/fix-scanner")
    
    # Ambil nilai Downtime
    dt_enable = config.getboolean("DOWNTIME_CONFIG", "ENABLE", fallback=True)
    dt_line_no = config.get("DOWNTIME_CONFIG", "LINE_NO", fallback="1").strip()
    dt_url = config.get("DOWNTIME_CONFIG", "API_URL", fallback="https://api.pms.yuasa.seavihive.com/api/fix-scanner-downtime")
    dt_log_file = config.get("DOWNTIME_CONFIG", "DOWNTIME_LOG_FILENAME", fallback="downtime_log.txt")
    dt_save_loc = config.get("DOWNTIME_CONFIG", "SAVE_LOCATION", fallback="desktop").strip().lower()
    
    dt_conn_mode = config.get("DOWNTIME_CONFIG", "CONNECTION_MODE", fallback="cx_programmer").strip().lower()
    dt_plc_ip = config.get("DOWNTIME_CONFIG", "PLC_IP", fallback="192.168.1.10").strip()
    dt_plc_port = config.get("DOWNTIME_CONFIG", "PLC_PORT", fallback="COM5").strip()
    dt_plc_baud = config.getint("DOWNTIME_CONFIG", "PLC_BAUD", fallback=9600)
    dt_addresses_raw = config.get("DOWNTIME_CONFIG", "DOWNTIME_ADDRESSES", fallback="")
    
    # Ambil nilai Printer
    pr_enable = config.getboolean("PRINTER_CONFIG", "ENABLE", fallback=True)
    pr_name = config.get("PRINTER_CONFIG", "PRINTER_NAME", fallback="TSC TL241")
    pr_url = config.get("PRINTER_CONFIG", "API_URL", fallback="https://api.pms.yuasa.seavihive.com/api/fix-scanner-pallet")
    pr_monitor_addr = config.get("PRINTER_CONFIG", "MONITOR_ADDRESS", fallback="0.05")
    pr_conn_mode = config.get("PRINTER_CONFIG", "CONNECTION_MODE", fallback="cx_programmer").strip().lower()
    pr_plc_ip = config.get("PRINTER_CONFIG", "PLC_IP", fallback="192.168.1.20/1").strip()
    pr_api_line = config.get("PRINTER_CONFIG", "API_LINE_NO", fallback="1")
    pr_label_line = config.get("PRINTER_CONFIG", "LABEL_LINE_NO", fallback="01")
    pr_retry_url = config.get("PRINTER_CONFIG", "RETRY_API_URL", fallback="https://api.pms.yuasa.seavihive.com/api/fix-scanner-pallet-retry")
    
    # Paper size settings
    pr_width = config.getint("PRINTER_CONFIG", "LABEL_WIDTH", fallback=40)
    pr_height = config.getint("PRINTER_CONFIG", "LABEL_HEIGHT", fallback=30)
    pr_gap = config.getint("PRINTER_CONFIG", "LABEL_GAP", fallback=2)
    pr_orientation = config.get("PRINTER_CONFIG", "LABEL_ORIENTATION", fallback="portrait").strip().lower()
    
    # Ambil nilai Timbangan Rockwell / Universal
    tb_enable = config.getboolean("TIMBANGAN_CONFIG", "ENABLE", fallback=True)
    tb_line = config.get("TIMBANGAN_CONFIG", "LINE_NO", fallback="14")
    tb_url = config.get("TIMBANGAN_CONFIG", "API_URL", fallback="https://api.pms.yuasa.seavihive.com/api/fix-scanner-masterbox")
    tb_retry_url = config.get("TIMBANGAN_CONFIG", "RETRY_API_URL", fallback="https://api.pms.yuasa.seavihive.com/api/fix-scanner-masterbox-retry")
    tb_width = config.getint("TIMBANGAN_CONFIG", "LABEL_WIDTH", fallback=75)
    tb_height = config.getint("TIMBANGAN_CONFIG", "LABEL_HEIGHT", fallback=100)
    tb_gap = config.getint("TIMBANGAN_CONFIG", "LABEL_GAP", fallback=2)
    tb_orientation = config.get("TIMBANGAN_CONFIG", "LABEL_ORIENTATION", fallback="landscape").strip().lower()
    
    tb_conn_mode = config.get("TIMBANGAN_CONFIG", "CONNECTION_MODE", fallback="rockwell").strip().lower()
    tb_plc_ip = config.get("TIMBANGAN_CONFIG", "PLC_IP", fallback="192.168.1.20/1").strip()
    tb_plc_port = config.get("TIMBANGAN_CONFIG", "PLC_PORT", fallback="COM6").strip()
    tb_plc_baud = config.getint("TIMBANGAN_CONFIG", "PLC_BAUD", fallback=9600)
    
    tb_tag_weight = config.get("TIMBANGAN_CONFIG", "TAG_WEIGHT", fallback="Recent_Weight").strip()
    tb_tag_qty = config.get("TIMBANGAN_CONFIG", "TAG_QTY", fallback="Recent_Qty").strip()
    tb_tag_type = config.get("TIMBANGAN_CONFIG", "TAG_TYPE", fallback="Product_Type").strip()
    tb_tag_totalizer = config.get("TIMBANGAN_CONFIG", "TAG_TOTALIZER", fallback="Totalizer_Box").strip()
    
    # Parse List Alamat Downtime
    dt_addresses = []
    if dt_addresses_raw:
        for item in dt_addresses_raw.split(","):
            parts = item.strip().split(":")
            if len(parts) >= 2:
                sym = parts[0].strip()
                addr = parts[1].strip()
                comment = parts[2].strip() if len(parts) >= 3 else sym
                dt_addresses.append({
                    "symbol": sym,
                    "address": addr,
                    "comment": comment
                })

    # Resolusi folder penyimpanan untuk file log
    if dt_save_loc == "desktop":
        # Abaikan desktop, paksa ke logs/downtime untuk kerapian
        save_dir = LOG_DIR_DOWNTIME
    else:
        save_dir = LOG_DIR_DOWNTIME
        
    downtime_log_path = os.path.join(save_dir, dt_log_file)
    
    return (scanner_enable, line_no, scanner_port, scanner_baud, scanner_url, 
            dt_enable, dt_line_no, dt_url, downtime_log_path, dt_conn_mode, dt_plc_ip, dt_plc_port, dt_plc_baud, dt_addresses,
            pr_enable, pr_name, pr_url, pr_retry_url, pr_monitor_addr, pr_api_line, pr_label_line,
            pr_conn_mode, pr_plc_ip, pr_width, pr_height, pr_gap, pr_orientation,
            tb_enable, tb_line, tb_url, tb_retry_url, tb_width, tb_height, tb_gap, tb_orientation,
            tb_conn_mode, tb_plc_ip, tb_plc_port, tb_plc_baud, tb_tag_weight, tb_tag_qty, tb_tag_type, tb_tag_totalizer)

(SCANNER_ENABLE, LINE_NO, PORT_SCANNER, BAUD_RATE, API_URL, 
 DOWNTIME_ENABLE, DOWNTIME_LINE_NO, DOWNTIME_API_URL, DOWNTIME_LOG_PATH, DOWNTIME_CONN_MODE, DOWNTIME_PLC_IP, DOWNTIME_PLC_PORT, DOWNTIME_PLC_BAUD, DOWNTIME_ADDRESSES,
 PRINTER_ENABLE, PRINTER_NAME, PRINTER_API_URL, PRINTER_RETRY_API_URL, PRINTER_MONITOR_ADDR, PRINTER_API_LINE_NO, PRINTER_LABEL_LINE_NO,
 PRINTER_CONN_MODE, PRINTER_PLC_IP, PRINTER_WIDTH, PRINTER_HEIGHT, PRINTER_GAP, PRINTER_ORIENTATION,
 TIMBANGAN_ENABLE, TIMBANGAN_LINE_NO, TIMBANGAN_API_URL, TIMBANGAN_RETRY_API_URL, 
 TIMBANGAN_WIDTH, TIMBANGAN_HEIGHT, TIMBANGAN_GAP, TIMBANGAN_ORIENTATION,
 TIMBANGAN_CONN_MODE, TIMBANGAN_PLC_IP, TIMBANGAN_PLC_PORT, TIMBANGAN_PLC_BAUD,
 TIMBANGAN_TAG_WEIGHT, TIMBANGAN_TAG_QTY, TIMBANGAN_TAG_TYPE, TIMBANGAN_TAG_TOTALIZER) = load_config()

# Load http port configuration directly
try:
    config_http = configparser.ConfigParser()
    config_http.read(CONFIG_FILE)
    HTTP_PORT = config_http.getint("PRINTER_CONFIG", "HTTP_PORT", fallback=8080)
except Exception as e:
    HTTP_PORT = 8080

from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class PrintRequestHandler(BaseHTTPRequestHandler):
    app_instance = None
    
    def log_message(self, format, *args):
        logging.info(f"[HTTP-SERVER] {format%args}")

    def handle_print_request(self, is_retry):
        if self.app_instance:
            self.app_instance.after(0, self.app_instance.hit_api_pallet_and_print, is_retry)
            self.send_response_json({
                "status": "success", 
                "message": f"Pallet {'reprint' if is_retry else 'print'} triggered successfully"
            })
        else:
            self.send_response_json({"status": "error", "message": "App instance not ready"}, 500)

    def handle_test_print(self, is_masterbox):
        if self.app_instance:
            if is_masterbox:
                # Trigger Master Box test print
                self.app_instance.after(0, self.app_instance.execute_physical_print_masterbox, 
                                          "YBID.MB.250908.08.000001", "M221SDCAC20", "B.CH-YTZ5S (Wet-CF) YU-5", "15.44", "10", "25-Sep-2025", "260728100001")
                self.send_response_json({"status": "success", "message": "Test print Master Box triggered"})
            else:
                # Trigger Pallet test print
                mock_data = {
                    "code": "YBID.PLT.250908.000001",
                    "part_code": "M221SDCAC20",
                    "batt_type": "B.CH-YTZ5S (Wet-CF) YU-5",
                    "quantity": "64 Masterbox / 640 Pcs",
                    "date_str": "25-Sep-2025",
                    "customer": "AFM (PT. SANTI YOGA)",
                    "order_no": "11500007"
                }
                self.app_instance.after(0, self.app_instance.execute_physical_print, mock_data)
                self.send_response_json({"status": "success", "message": "Test print Pallet triggered"})
        else:
            self.send_response_json({"status": "error", "message": "App instance not ready"}, 500)

    def do_GET(self):
        if self.path == '/print-pallet':
            self.handle_print_request(False)
        elif self.path == '/reprint-pallet':
            self.handle_print_request(True)
        elif self.path == '/test-print-pallet':
            self.handle_test_print(False)
        elif self.path == '/test-print-masterbox':
            self.handle_test_print(True)
        elif self.path in ['/', '/status']:
            self.send_response_json({
                "status": "online",
                "device": "Yuasa Production System Bridge",
                "printer_name": PRINTER_NAME,
                "line_no": PRINTER_API_LINE_NO,
                "http_port": HTTP_PORT
            })
        else:
            self.send_response_json({"status": "error", "message": "Endpoint not found"}, 404)

    def do_POST(self):
        if self.path == '/print-pallet':
            self.handle_print_request(False)
        elif self.path == '/reprint-pallet':
            self.handle_print_request(True)
        elif self.path == '/test-print-pallet':
            self.handle_test_print(False)
        elif self.path == '/test-print-masterbox':
            self.handle_test_print(True)
        else:
            self.send_response_json({"status": "error", "message": "Endpoint not found"}, 404)

    def send_response_json(self, data, status_code=200):
        try:
            response_bytes = json.dumps(data).encode('utf-8')
            self.send_response(status_code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(response_bytes)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response_bytes)
        except Exception as e:
            logging.error(f"[HTTP-SERVER] Error sending response: {e}")

# --- APLIKASI GUI TKINTER ---
class ScannerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self.title("Yuasa Production System Bridge App")
        self.geometry("820x680")
        self.minsize(800, 600)
        self.configure(bg="#f1f5f9")
        
        self.running = True
        self.sim_counter = 0
        
        # State variables Scanner
        self.ser = None
        self.scanner_status = tk.StringVar(value="MEMULAI...")
        self.scanner_color = tk.StringVar(value="#64748b")
        
        # State variables Downtime PLC
        self.plc_status = tk.StringVar(value="DOWNTIME INACTIVE" if not DOWNTIME_ENABLE else "MENGHUBUNGKAN...")
        self.plc_color = tk.StringVar(value="#64748b" if not DOWNTIME_ENABLE else "#f59e0b")
        self.plc_machine_state = tk.StringVar(value="-")
        
        # State variables Auto Printer (Pallet)
        self.printer_status = tk.StringVar(value="PRINTER INACTIVE" if not PRINTER_ENABLE else "MEMERIKSA...")
        self.printer_color = tk.StringVar(value="#64748b" if not PRINTER_ENABLE else "#f59e0b")
        self.printer_info_state = tk.StringVar(value="-")
        
        # State variables Timbangan (Universal)
        self.timbangan_status = tk.StringVar(value="TIMBANGAN INACTIVE" if not TIMBANGAN_ENABLE else "MENGHUBUNGKAN...")
        self.timbangan_color = tk.StringVar(value="#64748b" if not TIMBANGAN_ENABLE else "#f59e0b")
        self.timbangan_info_state = tk.StringVar(value="-")
        
        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Start Scanner Thread
        if SCANNER_ENABLE:
            self.scanner_thread = threading.Thread(target=self.scanner_loop, daemon=True)
            self.scanner_thread.start()
        else:
            self.scanner_status.set("SCANNER INACTIVE")
            self.scanner_color.set("#64748b")
        
        # Start PLC Downtime Thread
        if DOWNTIME_ENABLE or (PRINTER_ENABLE and PRINTER_CONN_MODE == "cx_programmer"):
            self.plc_thread = threading.Thread(target=self.plc_loop, daemon=True)
            self.plc_thread.start()
            
        # Start Printer Rockwell Thread
        if PRINTER_ENABLE and PRINTER_CONN_MODE == "rockwell":
            self.printer_rock_thread = threading.Thread(target=self.printer_rockwell_loop, daemon=True)
            self.printer_rock_thread.start()
        
        # UI init states
        if not PRINTER_ENABLE:
            self.printer_status.set("PRINTER INACTIVE")
            self.printer_color.set("#64748b")
                
        # Start Timbangan Thread
        if TIMBANGAN_ENABLE:
            self.timbangan_thread = threading.Thread(target=self.timbangan_loop, daemon=True)
            self.timbangan_thread.start()
        else:
            self.timbangan_status.set("TIMBANGAN INACTIVE")
            self.timbangan_color.set("#64748b")
            
        # Start HTTP Server for Handheld/Mobile Printing
        if PRINTER_ENABLE:
            self.http_thread = threading.Thread(target=self.start_http_server, daemon=True)
            self.http_thread.start()
                
        # Start Watchdog Monitor Thread (Jalankan selalu agar simulasi via GUI tetap berfungsi)
        if not WATCHDOG_AVAILABLE:
            logging.error("Library watchdog tidak ditemukan! Folder Monitor dinonaktifkan.")
            self.add_history("ERROR: 'watchdog' tidak terpasang. Auto-POST file log mati.")
        else:
            self.watcher_thread = threading.Thread(target=self.watcher_loop, daemon=True)
            self.watcher_thread.start()
        
    def create_widgets(self):
        # 1. Header Banner
        header = tk.Frame(self, bg="#0f172a", height=60)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)
        
        lbl_title = tk.Label(header, text="PT. YUASA BATTERY INDONESIA", font=("Arial", 14, "bold"), fg="#ffffff", bg="#0f172a")
        lbl_title.pack(anchor=tk.W, padx=15, pady=8, side=tk.LEFT)
        
        lbl_line = tk.Label(header, text=f"LINE SCANNER: {LINE_NO} | LINE TIMBANGAN: {TIMBANGAN_LINE_NO}", font=("Arial", 11, "bold"), fg="#38bdf8", bg="#0f172a")
        lbl_line.pack(anchor=tk.E, padx=15, pady=12, side=tk.RIGHT)
        
        # 2. Connection Status Panel (Empat Kolom)
        status_panel = tk.Frame(self, bg="#f1f5f9")
        status_panel.pack(fill=tk.X, padx=15, pady=8)
        
        # Kolom 1: Scanner
        scanner_frame = tk.LabelFrame(status_panel, text="Koneksi QR Scanner", font=("Arial", 8, "bold"), fg="#475569", bg="#f1f5f9", padx=8, pady=4)
        scanner_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)
        
        self.scanner_status_box = tk.Label(scanner_frame, textvariable=self.scanner_status, font=("Arial", 8, "bold"), fg="#ffffff", bg=self.scanner_color.get(), height=2)
        self.scanner_status_box.pack(fill=tk.X, pady=1)
        
        lbl_scanner_info = tk.Label(scanner_frame, text=f"Port: {PORT_SCANNER} | Baud: {BAUD_RATE}", font=("Arial", 7), fg="#64748b", bg="#f1f5f9")
        lbl_scanner_info.pack(anchor=tk.W)
        
        # Kolom 2: PLC Downtime
        plc_frame = tk.LabelFrame(status_panel, text="PLC Downtime", font=("Arial", 8, "bold"), fg="#475569", bg="#f1f5f9", padx=8, pady=4)
        plc_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)
        
        self.plc_status_box = tk.Label(plc_frame, textvariable=self.plc_status, font=("Arial", 8, "bold"), fg="#ffffff", bg=self.plc_color.get(), height=2)
        self.plc_status_box.pack(fill=tk.X, pady=1)
        
        self.lbl_plc_info = tk.Label(plc_frame, textvariable=self.plc_machine_state, font=("Arial", 7, "bold"), fg="#475569", bg="#f1f5f9")
        self.lbl_plc_info.pack(anchor=tk.W)
        
        # Kolom 3: Auto Printer
        pr_frame = tk.LabelFrame(status_panel, text="Auto Printer", font=("Arial", 8, "bold"), fg="#475569", bg="#f1f5f9", padx=8, pady=4)
        pr_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)
        
        self.pr_status_box = tk.Label(pr_frame, textvariable=self.printer_status, font=("Arial", 8, "bold"), fg="#ffffff", bg=self.printer_color.get(), height=2)
        self.pr_status_box.pack(fill=tk.X, pady=1)
        
        self.lbl_pr_info = tk.Label(pr_frame, textvariable=self.printer_info_state, font=("Arial", 7, "bold"), fg="#475569", bg="#f1f5f9")
        self.lbl_pr_info.pack(anchor=tk.W)
        
        # Kolom 4: PLC Timbangan
        tb_frame = tk.LabelFrame(status_panel, text="PLC Timbangan", font=("Arial", 8, "bold"), fg="#475569", bg="#f1f5f9", padx=8, pady=4)
        tb_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)
        
        self.tb_status_box = tk.Label(tb_frame, textvariable=self.timbangan_status, font=("Arial", 8, "bold"), fg="#ffffff", bg=self.timbangan_color.get(), height=2)
        self.tb_status_box.pack(fill=tk.X, pady=1)
        
        self.lbl_tb_info = tk.Label(tb_frame, textvariable=self.timbangan_info_state, font=("Arial", 7, "bold"), fg="#475569", bg="#f1f5f9")
        self.lbl_tb_info.pack(anchor=tk.W)
        
        # 3. Info Detail Path & API
        detail_info_frame = tk.Frame(self, bg="#e2e8f0", bd=1, relief=tk.SOLID)
        detail_info_frame.pack(fill=tk.X, padx=15, pady=2)
        
        info_text = (
            f"API Scanner : {API_URL}\n"
            f"API Pallet  : {PRINTER_API_URL if PRINTER_ENABLE else 'INACTIVE'} (Mode: {DOWNTIME_CONN_MODE} -> Printer: {PRINTER_NAME} [{PRINTER_WIDTH}x{PRINTER_HEIGHT}mm])\n"
            f"API MasterBox: {TIMBANGAN_API_URL if TIMBANGAN_ENABLE else 'INACTIVE'} (Mode: {TIMBANGAN_CONN_MODE} -> IP: {TIMBANGAN_PLC_IP})"
        )
        lbl_paths = tk.Label(detail_info_frame, text=info_text, font=("Courier New", 8), fg="#475569", bg="#e2e8f0", justify=tk.LEFT)
        lbl_paths.pack(anchor=tk.W, padx=10, pady=4)
        
        # 4. Simulation Testing Panel
        self.sim_frame = tk.LabelFrame(self, text="Simulator Testing Timbangan (Mock Timbang Tanpa PLC)", font=("Arial", 9, "bold"), fg="#0f172a", bg="#f1f5f9", padx=10, pady=5)
        self.sim_frame.pack(fill=tk.X, padx=15, pady=4)
        
        # Input simulasi
        row1 = tk.Frame(self.sim_frame, bg="#f1f5f9")
        row1.pack(fill=tk.X, pady=2)
        tk.Label(row1, text="Part Code / Product Type:", font=("Arial", 8, "bold"), fg="#475569", bg="#f1f5f9").pack(side=tk.LEFT, padx=2)
        self.entry_sim_part_code = tk.Entry(row1, font=("Arial", 8), width=50)
        self.entry_sim_part_code.pack(side=tk.LEFT, padx=5)
        self.entry_sim_part_code.insert(0, "M221SDCAC20 B.CH-YTZ5S (Wet-CF) YU-5")
        
        row2 = tk.Frame(self.sim_frame, bg="#f1f5f9")
        row2.pack(fill=tk.X, pady=2)
        tk.Label(row2, text="Berat (KG):", font=("Arial", 8, "bold"), fg="#475569", bg="#f1f5f9").pack(side=tk.LEFT, padx=2)
        self.entry_sim_weight = tk.Entry(row2, font=("Arial", 8), width=10)
        self.entry_sim_weight.pack(side=tk.LEFT, padx=5)
        self.entry_sim_weight.insert(0, "15.44")
        
        tk.Label(row2, text="Quantity (PCS):", font=("Arial", 8, "bold"), fg="#475569", bg="#f1f5f9").pack(side=tk.LEFT, padx=15)
        self.entry_sim_qty = tk.Entry(row2, font=("Arial", 8), width=8)
        self.entry_sim_qty.pack(side=tk.LEFT, padx=5)
        self.entry_sim_qty.insert(0, "10")
        
        btn_sim = tk.Button(row2, text="Kirim Simulasi Timbang (Simulasi Box Baru)", font=("Arial", 8, "bold"), fg="#ffffff", bg="#0ea5e9", command=self.trigger_simulation, padx=10)
        btn_sim.pack(side=tk.RIGHT, padx=5)
        
        # 5. History Table
        history_title = tk.Label(self, text="Riwayat Aktivitas Sistem Terpadu:", font=("Arial", 10, "bold"), fg="#1e293b", bg="#f1f5f9")
        history_title.pack(anchor=tk.W, padx=15, pady=(5, 1))
        
        table_frame = tk.Frame(self, bg="#ffffff")
        table_frame.pack(expand=True, fill=tk.BOTH, padx=15, pady=3)
        
        scrollbar = tk.Scrollbar(table_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.lst_history = tk.Listbox(table_frame, font=("Courier New", 9), yscrollcommand=scrollbar.set, bg="#ffffff", fg="#1e293b", selectbackground="#cbd5e1")
        self.lst_history.pack(expand=True, fill=tk.BOTH, side=tk.LEFT)
        scrollbar.config(command=self.lst_history.yview)
        
        # 6. Footer Buttons
        footer = tk.Frame(self, bg="#f1f5f9", height=40)
        footer.pack(fill=tk.X, side=tk.BOTTOM, padx=15, pady=5)
        
        btn_open_log = ttk.Button(footer, text="Open Log Folder", command=self.open_log_folder)
        btn_open_log.pack(side=tk.LEFT, padx=5)
        
        btn_clear = ttk.Button(footer, text="Clear History", command=self.clear_history)
        btn_clear.pack(side=tk.RIGHT, padx=5)
        
    def set_scanner_status(self, text, color):
        self.scanner_status.set(text)
        self.scanner_color.set(color)
        self.scanner_status_box.configure(bg=color)
        
    def set_plc_status(self, text, color, info_state):
        self.plc_status.set(text)
        self.plc_color.set(color)
        self.plc_status_box.configure(bg=color)
        self.plc_machine_state.set(info_state)
        
    def set_printer_status(self, text, color, info_state):
        self.printer_status.set(text)
        self.printer_color.set(color)
        self.pr_status_box.configure(bg=color)
        self.printer_info_state.set(info_state)
        
    def set_timbangan_status(self, text, color, info_state):
        self.timbangan_status.set(text)
        self.timbangan_color.set(color)
        self.tb_status_box.configure(bg=color)
        self.timbangan_info_state.set(info_state)
        
    def add_history(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {msg}"
        self.lst_history.insert(tk.END, formatted_msg)
        self.lst_history.yview(tk.END)
        
    def open_log_folder(self):
        try:
            if os.name == 'nt':
                os.startfile(LOG_DIR)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', LOG_DIR])
            else:
                subprocess.Popen(['xdg-open', LOG_DIR])
        except Exception as e:
            messagebox.showerror("Error", f"Gagal membuka folder log: {e}")
            
    def clear_history(self):
        self.lst_history.delete(0, tk.END)
        
    def check_printer_connection(self):
        if not PYWIN32_AVAILABLE:
            return False
        try:
            hPrinter = win32print.OpenPrinter(PRINTER_NAME)
            win32print.ClosePrinter(hPrinter)
            return True
        except Exception:
            return False

    # --- READ PLC UNIVERSAL FUNCTION ---
    def get_omron_address_value(self, conn_mode, plc_ip, plc_port, plc_baud, address_str, list_view_cache=None):
        """Membaca nilai dari OMRON PLC menggunakan mode yang dipilih"""
        area_type, word, bit = parse_omron_address(address_str)
        if area_type is None:
            return None
            
        if conn_mode == "cx_programmer" and list_view_cache is not None:
            # Scrape dari data watch window yang sudah dibaca
            for item in list_view_cache:
                if item.get("address") == address_str:
                    return item.get("value")
            return None
            
        elif conn_mode == "serial":
            words = OmronPLCHelper.read_words_serial(plc_port, plc_baud, area_type, word, 1)
            if words:
                val = words[0]
                if bit is not None:
                    return str((val >> bit) & 1)
                return str(val)
                
        elif conn_mode == "ethernet":
            # Default FINS port 9600
            words = OmronPLCHelper.read_words_fins_udp(plc_ip, 9600, area_type, word, 1)
            if words:
                val = words[0]
                if bit is not None:
                    return str((val >> bit) & 1)
                return str(val)
                
        return None

    # --- SIMULASI TESTING ---
    def trigger_simulation(self):
        """Simulasikan penulisan file log timbangan ketika klik tombol GUI"""
        try:
            part_code = self.entry_sim_part_code.get().strip()
            weight = float(self.entry_sim_weight.get().strip())
            qty = int(self.entry_sim_qty.get().strip())
            
            self.sim_counter += 1
            now = datetime.now()
            time_short = now.strftime("%H:%M")
            time_full = now.strftime("%d%m%Y %H:%M:%S")
            timestamp_file = now.strftime("%d%m%Y_%H%M%S")
            
            filename = os.path.join(
                LOG_DIR_TIMBANGAN,
                f"log_line_no_{TIMBANGAN_LINE_NO}_{timestamp_file}.txt"
            )
            
            lines = [
                f"ID: {self.sim_counter}",
                f"Line_No : {TIMBANGAN_LINE_NO}",
                f"Recent_Weight: {weight} (REAL)",
                f"Recent_Qty: {qty} (DINT)",
                f"Product_Type: {part_code} (STRING)",
                f"Timestamp: {time_full}",
                "----------------------------------------"
            ]
            
            with open(filename, "w", encoding="utf-8") as f:
                for l in lines:
                    f.write(l + "\n")
                    
            msg = f"Simulasi: Box Baru #{self.sim_counter} dicatat ({weight} KG, {qty} PCS)."
            self.add_history(msg)
            logging.info(f"[TIMBANGAN] {msg}")
            
        except ValueError:
            messagebox.showerror("Input Error", "Isian Berat harus angka desimal dan Quantity harus angka bulat!")

    # --- HTTP API & RAW PRINT LOGIC (SCANNER) ---
    def send_scanner_api(self, pack_code):
        payload = {
            "line_no": str(LINE_NO),
            "pack_code": pack_code
        }
        logging.info(f"[SCANNER] Mengirim data ke API: {payload}")
        
        try:
            start_time = time.time()
            headers = {'Content-Type': 'application/json'}
            response = requests.post(API_URL, json=payload, headers=headers, timeout=10)
            duration = time.time() - start_time
            res_body = response.text.strip()
            
            if response.status_code == 200:
                logging.info(f"[SCANNER] API Sukses ({response.status_code}) dalam {duration:.2f}s. Respon: {res_body}")
                self.after(0, self.add_history, f"SCAN OK -> QR: {pack_code} (200)")
            else:
                logging.error(f"[SCANNER] API Gagal ({response.status_code}). Respon: {res_body}")
                self.after(0, self.add_history, f"SCAN ERROR {response.status_code} -> QR: {pack_code}")
        except requests.exceptions.RequestException as e:
            logging.error(f"[SCANNER] Error Jaringan: {e}")
            self.after(0, self.add_history, f"SCAN JARINGAN ERROR -> Gagal Kirim QR: {pack_code}")
            
    def scanner_loop(self):
        while self.running:
            self.after(0, self.set_scanner_status, f"MENGHUBUNGKAN KE {PORT_SCANNER}...", "#f59e0b")
            self.after(0, self.add_history, f"Scanner: Menghubungkan ke {PORT_SCANNER}...")
            logging.info(f"[SCANNER] Mencoba membuka port {PORT_SCANNER}...")
            
            try:
                self.ser = serial.Serial(PORT_SCANNER, BAUD_RATE, timeout=1)
                logging.info(f"[SCANNER] Berhasil terhubung ke port {PORT_SCANNER}.")
                self.after(0, self.set_scanner_status, "SCANNER READY (TERHUBUNG)", "#22c55e")
                self.after(0, self.add_history, "Scanner: Siap digunakan.")
                
                while self.running:
                    if self.ser.in_waiting > 0:
                        try:
                            barcode_raw = self.ser.readline()
                            barcode_text = barcode_raw.decode('utf-8').strip()
                            
                            if barcode_text:
                                logging.info(f"[SCANNER] Terbaca: {barcode_text}")
                                self.after(0, self.add_history, f"SCAN: {barcode_text}")
                                self.after(0, self.set_scanner_status, "MENGIRIM KE API...", "#3b82f6")
                                
                                api_thread = threading.Thread(target=self.send_scanner_api, args=(barcode_text,), daemon=True)
                                api_thread.start()
                                
                                self.after(1500, lambda: self.set_scanner_status("SCANNER READY (TERHUBUNG)", "#22c55e") if self.ser and self.ser.is_open else None)
                        except Exception as e:
                            logging.error(f"[SCANNER] Error baca data: {e}")
                            break
                    time.sleep(0.05)
            except serial.SerialException as e:
                logging.error(f"[SCANNER] Gagal membuka port {PORT_SCANNER}: {e}")
                self.after(0, self.set_scanner_status, "TERPUTUS - RECONNECTING...", "#ef4444")
                self.after(0, self.add_history, f"Scanner: Gagal membuka {PORT_SCANNER} (Mencoba lagi...)")
                for _ in range(50):
                    if not self.running:
                        break
                    time.sleep(0.1)
            finally:
                if self.ser and self.ser.is_open:
                    self.ser.close()
                    self.ser = None
                    logging.info("[SCANNER] Serial ditutup.")

    # --- HTTP API & RAW PRINT LOGIC (DOWNTIME PLC) ---
    def send_downtime_api(self, symbol_name, address, status, comment, timestamp):
        payload = {
            "line_no": str(DOWNTIME_LINE_NO),
            "code_machine": symbol_name,
            "address": address,
            "status": status,
            "comment": comment,
            "timestamp_plc": timestamp
        }
        logging.info(f"[DOWNTIME] Mengirim data ke API: {payload}")
        
        try:
            start_time = time.time()
            headers = {"Content-Type": "application/json"}
            response = requests.post(DOWNTIME_API_URL, json=payload, headers=headers, timeout=5)
            duration = time.time() - start_time
            res_body = response.text.strip()
            
            if response.status_code == 200:
                logging.info(f"[DOWNTIME] API Sukses ({response.status_code}) dalam {duration:.2f}s. Respon: {res_body}")
                self.after(0, self.add_history, f"PLC OK -> {symbol_name} ({status})")
            else:
                logging.error(f"[DOWNTIME] API Gagal ({response.status_code}). Respon: {res_body}")
                self.after(0, self.add_history, f"PLC API ERROR {response.status_code} -> {symbol_name} ({status})")
        except Exception as e:
            logging.error(f"[DOWNTIME] Error Jaringan: {e}")
            self.after(0, self.add_history, f"PLC JARINGAN ERROR -> Gagal Kirim status {symbol_name}")

    # --- AUTOMATIC PRINTER TOMBOL LOGIC (win32print + TSPL) ---
    def hit_api_pallet_and_print(self, is_retry=False):
        """Memanggil API Pallet (atau retry jika is_retry=True), lalu mencetaknya jika data diperoleh"""
        url = PRINTER_RETRY_API_URL if is_retry else PRINTER_API_URL
        api_label = "REPRINT" if is_retry else "CETAK"
        
        self.after(0, self.set_printer_status, f"{api_label}: AMBIL DATA...", "#3b82f6", "Meminta pallet ID...")
        payload = {"line_no": str(PRINTER_API_LINE_NO)}
        
        logging.info(f"[PRINTER] Mengirim POST request ({api_label}) untuk Line {PRINTER_API_LINE_NO} ke {url}")
        
        try:
            start_time = time.time()
            response = requests.post(url, json=payload, timeout=8)
            duration = time.time() - start_time
            
            if response.status_code == 200:
                res_data = response.json()
                data = res_data.get("data", {})
                metadata = data.get("metaData", {})
                
                created_at_raw = data.get("createdAt", "")
                try:
                    dt_part = created_at_raw.split(".")[0]
                    dt = datetime.strptime(dt_part, "%Y-%m-%dT%H:%M:%S")
                    date_str = dt.strftime("%d-%b-%Y")
                except:
                    date_str = datetime.now().strftime("%d-%b-%Y")
                    
                raw_part_code = metadata.get("part_code", "-")
                parts = [p.strip() for p in raw_part_code.split(" ") if p.strip()]
                if len(parts) >= 2:
                    part_code = parts[0]
                    batt_type = " ".join(parts[1:])
                else:
                    part_code = raw_part_code
                    batt_type = "-"
                    
                customer = (
                    metadata.get("customer") or 
                    metadata.get("customer_name") or 
                    data.get("customer") or 
                    res_data.get("customer") or 
                    res_data.get("customerName") or 
                    res_data.get("customer_name") or 
                    "AFM (PT. SANTI YOGA)"
                )
                order_no = (
                    metadata.get("order_no") or 
                    metadata.get("no_order") or 
                    data.get("order_no") or 
                    res_data.get("orderNo") or 
                    res_data.get("order_no") or 
                    res_data.get("no_order") or 
                    "-"
                )
                
                pack_qty = (
                    res_data.get("quantityPack") or 
                    data.get("quantityPack") or 
                    metadata.get("quantityPack") or 
                    metadata.get("quantity_pack") or 
                    metadata.get("masterbox") or 
                    None
                )
                pcs_qty = (
                    res_data.get("quantityPcs") or 
                    data.get("quantityPcs") or 
                    metadata.get("quantityPcs") or 
                    metadata.get("quantity_pcs") or 
                    metadata.get("quantity") or 
                    None
                )
                
                if pack_qty is not None and pcs_qty is not None:
                    quantity_formatted = f"{pack_qty} Masterbox / {pcs_qty} Pcs"
                elif pcs_qty is not None:
                    quantity_formatted = f"{pcs_qty} Pcs"
                else:
                    quantity_formatted = str(metadata.get("quantity", "0 Pcs"))
                
                parsed_data = {
                    "code": data.get("code", "-"),
                    "part_code": part_code,
                    "batt_type": batt_type,
                    "quantity": quantity_formatted,
                    "date_str": date_str,
                    "customer": customer,
                    "order_no": order_no
                }
                
                logging.info(f"[PRINTER] API Sukses ({response.status_code}) dalam {duration:.2f}s. Pallet: {parsed_data['code']}")
                self.after(0, self.add_history, f"PRINTER API -> Sukses memuat Pallet: {parsed_data['code']}")
                
                # Pemicu cetak fisik
                self.execute_physical_print(parsed_data)
                
            else:
                logging.error(f"[PRINTER] API Gagal ({response.status_code}). Respon: {response.text.strip()}")
                self.after(0, self.add_history, f"PRINTER API ERROR ({response.status_code}) -> Gagal ambil data.")
                self.after(0, self.set_printer_status, "CETAK GAGAL (API ERROR)", "#ef4444", "Respons API salah")
                self.after(3000, lambda: self.reset_printer_visual_state())
                
        except Exception as e:
            logging.error(f"[PRINTER] Error Hit API Pallet: {e}")
            self.after(0, self.add_history, f"PRINTER JARINGAN ERROR -> Gagal hit API Pallet.")
            self.after(0, self.set_printer_status, "CETAK GAGAL (NET ERROR)", "#ef4444", "Masalah Jaringan")
            self.after(3000, lambda: self.reset_printer_visual_state())

    def execute_physical_print(self, data_dict):
        """Kirim perintah TSPL raw ke printer TSC"""
        if not PYWIN32_AVAILABLE:
            self.after(0, self.set_printer_status, "CETAK ERROR (DRV)", "#ef4444", "Library win32print missing")
            return
            
        code = data_dict.get("code", "-")
        part_code = data_dict.get("part_code", "-")
        batt_type = data_dict.get("batt_type", "-")
        quantity = data_dict.get("quantity", "0")
        date_str = data_dict.get("date_str", "-")
        customer = data_dict.get("customer", "AFM (PT. SANTI YOGA)")
        order_no = data_dict.get("order_no", "-")
        
        w_dots = int(PRINTER_WIDTH * 8)
        
        if PRINTER_WIDTH < 55:
            # Template Kecil (contoh 40mm x 30mm)
            tspl_command = f"""SIZE {PRINTER_WIDTH} mm, {PRINTER_HEIGHT} mm
GAP {PRINTER_GAP} mm, 0 mm
DIRECTION 1
CLS
TEXT 20,10,"2",0,1,1,"PT. YUASA BATTERY INDONESIA"
BAR 20,28,280,2
QRCODE 15,45,M,3,A,0,"{code}"
TEXT 105,45,"1",0,1,1,"Group Code : {code}"
TEXT 105,65,"1",0,1,1,"Order No.  : {order_no}"
TEXT 105,85,"1",0,1,1,"Customer   : {customer}"
TEXT 105,105,"1",0,1,1,"Part Code  : {part_code}"
TEXT 105,125,"1",0,1,1,"Batt. Type : {batt_type}"
TEXT 105,145,"1",0,1,1,"Quantity   : {quantity} PCS"
TEXT 105,165,"1",0,1,1,"Prod/Shf/Mc: {date_str}/I/{PRINTER_LABEL_LINE_NO}"
PRINT 1
"""
        elif PRINTER_HEIGHT <= 65 or PRINTER_WIDTH <= 80:
            # Template Sedang (70mm x 50mm) Sesuai Gambar 2 (Pallet Label)
            tspl_command = f"""SIZE {PRINTER_WIDTH} mm, {PRINTER_HEIGHT} mm
GAP {PRINTER_GAP} mm, 0 mm
DIRECTION 1
CLS
TEXT 20,100,"0",0,12,12,"PT. YUASA BATTERY INDONESIA"
BAR 20,128,440,3
QRCODE 20,160,M,5,A,0,"{code}"
TEXT 180,155,"0",0,7,7,"Group Code : {code}"
TEXT 180,188,"0",0,7,7,"Order No.  : {order_no}"
TEXT 180,221,"0",0,7,7,"Customer   : {customer}"
TEXT 180,254,"0",0,7,7,"Part Code  : {part_code}"
TEXT 180,287,"0",0,7,7,"Batt. Type : {batt_type}"
TEXT 180,320,"0",0,7,7,"Quantity   : {quantity}"
TEXT 180,353,"0",0,7,7,"Prod. /Shift/Mc : {date_str}/I/{PRINTER_LABEL_LINE_NO}"
PRINT 1
"""
        else:
            # Template Besar (contoh 75mm x 100mm)
            if PRINTER_ORIENTATION == "landscape":
                # Layout Landscape (orientasi menyamping, teks diputar 90 derajat)
                tspl_command = f"""SIZE {PRINTER_WIDTH} mm, {PRINTER_HEIGHT} mm
GAP {PRINTER_GAP} mm, 0 mm
DIRECTION 1
CLS
TEXT 540,40,"3",90,1,1,"PT. YUASA BATTERY INDONESIA"
BAR 510,40,4,720
QRCODE 360,40,M,6,A,90,"{code}"
TEXT 440,300,"2",90,1,1,"Group Code : {code}"
TEXT 400,300,"2",90,1,1,"Order No.  : {order_no}"
TEXT 360,300,"2",90,1,1,"Customer   : {customer}"
TEXT 320,300,"2",90,1,1,"Part Code  : {part_code}"
TEXT 280,300,"2",90,1,1,"Batt. Type : {batt_type}"
TEXT 240,300,"2",90,1,1,"Quantity   : {quantity} PCS"
TEXT 200,300,"2",90,1,1,"Prod/Shf/Mc: {date_str}/I/{PRINTER_LABEL_LINE_NO}"
PRINT 1
"""
            else:
                # Layout Portrait (orientasi normal tegak lurus)
                tspl_command = f"""SIZE {PRINTER_WIDTH} mm, {PRINTER_HEIGHT} mm
GAP {PRINTER_GAP} mm, 0 mm
DIRECTION 1
CLS
TEXT 40,20,"3",0,1,1,"PT. YUASA BATTERY INDONESIA"
BAR 40,56,{w_dots - 80},4
QRCODE 40,90,M,6,A,0,"{code}"
TEXT 280,90,"2",0,1,1,"Group Code : {code}"
TEXT 280,130,"2",0,1,1,"Order No.  : {order_no}"
TEXT 280,170,"2",0,1,1,"Customer   : {customer}"
TEXT 280,210,"2",0,1,1,"Part Code  : {part_code}"
TEXT 280,250,"2",0,1,1,"Batt. Type : {batt_type}"
TEXT 280,290,"2",0,1,1,"Quantity   : {quantity} PCS"
TEXT 280,330,"2",0,1,1,"Prod/Shf/Mc: {date_str}/I/{PRINTER_LABEL_LINE_NO}"
PRINT 1
"""
        self.after(0, self.set_printer_status, "MENCETAK KERTAS...", "#3b82f6", f"QR: {code}")
        logging.info(f"[PRINTER] Mengirim raw data ke {PRINTER_NAME}...")
        
        try:
            hPrinter = win32print.OpenPrinter(PRINTER_NAME)
            try:
                hJob = win32print.StartDocPrinter(hPrinter, 1, ("PLC Auto QR Label", None, "RAW"))
                try:
                    win32print.StartPagePrinter(hPrinter)
                    win32print.WritePrinter(hPrinter, tspl_command.encode('utf-8'))
                    win32print.EndPagePrinter(hPrinter)
                    logging.info(f"[PRINTER] Sukses mencetak label QR Pallet: {code}")
                    self.after(0, self.add_history, f"PRINTER -> Sukses mencetak QR: {code}")
                finally:
                    win32print.EndDocPrinter(hPrinter)
            finally:
                win32print.ClosePrinter(hPrinter)
                
            self.after(0, self.set_printer_status, "SUKSES MENCETAK", "#22c55e", f"Pallet {code}")
            self.after(2000, lambda: self.reset_printer_visual_state())
            
        except Exception as e:
            logging.error(f"[PRINTER] Gagal cetak ke {PRINTER_NAME}: {e}")
            self.after(0, self.add_history, f"PRINTER ERROR -> Gagal cetak ke printer.")
            self.after(0, self.set_printer_status, "CETAK ERROR (SYS)", "#ef4444", str(e)[:30])
            self.after(3000, lambda: self.reset_printer_visual_state())

    def reset_printer_visual_state(self):
        if not self.running:
            return
        if self.check_printer_connection():
            self.set_printer_status("PRINTER READY", "#22c55e", f"Target: {PRINTER_NAME}")
        else:
            self.set_printer_status("PRINTER NOT FOUND", "#ef4444", f"Mencari: {PRINTER_NAME}")

    # --- HTTP API & RAW PRINT LOGIC (MASTER BOX) ---
    def execute_physical_print_masterbox(self, code, part_code, batt_type, weight, quantity, date_str, code_production="-"):
        """Mencetak stiker QR Master Box (Layout sesuai gambar landscape)"""
        if not PYWIN32_AVAILABLE:
            logging.error("[MASTERBOX] Library win32print missing. Cetak fisik dibatalkan.")
            return
            
        w_dots = int(TIMBANGAN_WIDTH * 8)
        
        if TIMBANGAN_WIDTH < 55:
            # Layout Kecil 4x3 cm
            tspl_command = f"""SIZE {TIMBANGAN_WIDTH} mm, {TIMBANGAN_HEIGHT} mm
GAP {TIMBANGAN_GAP} mm, 0 mm
DIRECTION 1
CLS
TEXT 20,10,"2",0,1,1,"PT. YUASA BATTERY INDONESIA"
BAR 20,28,280,2
QRCODE 15,45,M,3,A,0,"{code}"
TEXT 105,45,"1",0,1,1,"{code}"
TEXT 105,65,"1",0,1,1,"Part Code  : {part_code}"
TEXT 105,85,"1",0,1,1,"TYPE       : {batt_type}"
TEXT 105,105,"1",0,1,1,"Quantity   : {quantity} Pcs"
TEXT 105,125,"1",0,1,1,"BERAT      : {weight} KG"
TEXT 105,145,"1",0,1,1,"Prd/Shf/Mc : {date_str}/I/{TIMBANGAN_LINE_NO}"
TEXT 105,165,"1",0,1,1,"Kode Prod  : {code_production}"
PRINT 2
"""
        elif TIMBANGAN_HEIGHT <= 65 or TIMBANGAN_WIDTH <= 80:
            # Layout Sedang (70mm x 50mm) Sesuai Gambar 1 (Master Box Label dengan Sedikit Margin Atas Y=40)
            tspl_command = f"""SIZE {TIMBANGAN_WIDTH} mm, {TIMBANGAN_HEIGHT} mm
GAP {TIMBANGAN_GAP} mm, 0 mm
DIRECTION 1
CLS
TEXT 20,40,"0",0,12,12,"PT. YUASA BATTERY INDONESIA"
BAR 20,68,440,3
QRCODE 20,100,M,5,A,0,"{code}"
TEXT 180,95,"0",0,8,8,"{code}"
TEXT 180,135,"0",0,7,7,"Part Code  : {part_code}"
TEXT 180,175,"0",0,7,7,"TYPE       : {batt_type}"
TEXT 180,215,"0",0,7,7,"Quantity   : {quantity} Pcs    BERAT : {weight} KG"
TEXT 180,255,"0",0,7,7,"Prd/Shift/Mc : {date_str}/I/{TIMBANGAN_LINE_NO}"
TEXT 180,290,"0",0,7,7,"Kode Prod    : {code_production}"
PRINT 2
"""
        else:
            # Layout Besar 7.5x10 cm
            if TIMBANGAN_ORIENTATION == "landscape":
                # Sesuai Gambar (Landscape Rotated 90)
                tspl_command = f"""SIZE {TIMBANGAN_WIDTH} mm, {TIMBANGAN_HEIGHT} mm
GAP {TIMBANGAN_GAP} mm, 0 mm
DIRECTION 1
CLS
TEXT 540,40,"3",90,1,1,"PT. YUASA BATTERY INDONESIA"
BAR 510,40,4,720
QRCODE 360,40,M,6,A,90,"{code}"
TEXT 440,300,"2",90,1,2,"{code}"
TEXT 400,300,"2",90,1,1,"Part Code  : {part_code}"
TEXT 360,300,"2",90,1,1,"TYPE       : {batt_type}"
TEXT 320,300,"2",90,1,1,"Quantity   : {quantity} Pcs  BERAT : {weight} KG"
TEXT 280,300,"2",90,1,1,"Prd/Shift/Mc: {date_str}/I/{TIMBANGAN_LINE_NO}"
TEXT 240,300,"2",90,1,1,"Kode Prod   : {code_production}"
PRINT 2
"""
            else:
                # Portrait
                tspl_command = f"""SIZE {TIMBANGAN_WIDTH} mm, {TIMBANGAN_HEIGHT} mm
GAP {TIMBANGAN_GAP} mm, 0 mm
DIRECTION 1
CLS
TEXT 40,20,"3",0,1,1,"PT. YUASA BATTERY INDONESIA"
BAR 40,56,{w_dots - 80},4
QRCODE 40,90,M,6,A,0,"{code}"
TEXT 280,90,"2",0,1,2,"{code}"
TEXT 280,130,"2",0,1,1,"Part Code  : {part_code}"
TEXT 280,170,"2",0,1,1,"TYPE       : {batt_type}"
TEXT 280,210,"2",0,1,1,"Quantity   : {quantity} Pcs  BERAT : {weight} KG"
TEXT 280,250,"2",0,1,1,"Prd/Shift/Mc: {date_str}/I/{TIMBANGAN_LINE_NO}"
TEXT 280,290,"2",0,1,1,"Kode Prod   : {code_production}"
PRINT 2
"""
        logging.info(f"[MASTERBOX] Mengirim raw data Master Box ke {PRINTER_NAME}...")
        try:
            hPrinter = win32print.OpenPrinter(PRINTER_NAME)
            try:
                hJob = win32print.StartDocPrinter(hPrinter, 1, ("PLC Auto MasterBox Label", None, "RAW"))
                try:
                    win32print.StartPagePrinter(hPrinter)
                    win32print.WritePrinter(hPrinter, tspl_command.encode('utf-8'))
                    win32print.EndPagePrinter(hPrinter)
                    logging.info(f"[MASTERBOX] Sukses mencetak Master Box QR: {code}")
                    self.after(0, self.add_history, f"MASTERBOX -> Sukses mencetak QR: {code}")
                finally:
                    win32print.EndDocPrinter(hPrinter)
            finally:
                win32print.ClosePrinter(hPrinter)
        except Exception as e:
            logging.error(f"[MASTERBOX] Gagal cetak ke {PRINTER_NAME}: {e}")
            self.after(0, self.add_history, f"MASTERBOX ERROR -> Gagal cetak stiker Master Box.")

    def send_masterbox_api_and_print(self, payload, file_path):
        """Kirim data timbangan ke API Masterbox, lalu trigger print label otomatis"""
        file_name = os.path.basename(file_path)
        logging.info(f"[MASTERBOX] Mengirim data ke API Master Box: {payload}")
        
        url = TIMBANGAN_API_URL
        headers = {'Content-Type': 'application/json'}
        success = False
        
        try:
            # Bersihkan part_code dari null bytes dan suffix tipe data sebelum kirim
            if 'part_code' in payload:
                import re
                clean_pc = payload['part_code'].replace('\x00', '').strip()
                clean_pc = re.sub(r'\s*\([A-Z_]+\)\s*$', '', clean_pc).strip()
                payload['part_code'] = clean_pc
            
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            if response.status_code in [200, 201]:
                res_data = response.json()
                data = res_data.get("data", {})
                code = data.get("code", "MOCK.MB.CODE.ERROR")
                
                metadata = data.get("metaData", {})
                raw_part_code = metadata.get("part_code", payload.get("part_code", "-"))
                parts = [p.strip() for p in raw_part_code.split(" ") if p.strip()]
                if len(parts) >= 2:
                    part_code = parts[0]
                    batt_type = " ".join(parts[1:])
                else:
                    part_code = raw_part_code
                    batt_type = "-"
                
                # Parsing tanggal
                created_at_raw = data.get("createdAt", "")
                try:
                    dt_part = created_at_raw.split(".")[0]
                    dt = datetime.strptime(dt_part, "%Y-%m-%dT%H:%M:%S")
                    date_str = dt.strftime("%d-%b-%Y")
                except:
                    date_str = datetime.now().strftime("%d-%b-%Y")
                
                code_production = (
                    data.get("codeProduction") or 
                    data.get("code_production") or 
                    res_data.get("codeProduction") or 
                    res_data.get("code_production") or 
                    metadata.get("codeProduction") or 
                    metadata.get("code_production") or 
                    "-"
                )
                
                logging.info(f"[MASTERBOX] API Sukses ({response.status_code}). Code: {code}, CodeProd: {code_production}")
                self.after(0, self.add_history, f"MASTERBOX API -> Sukses. QR: {code}")
                
                # Auto-print Masterbox
                self.execute_physical_print_masterbox(
                    code=code,
                    part_code=part_code,
                    batt_type=batt_type,
                    weight=payload.get("weight", "0.0"),
                    quantity=payload.get("quantity", "0"),
                    date_str=date_str,
                    code_production=code_production
                )
                success = True
            else:
                res_body = response.text.strip()
                logging.error(f"[MASTERBOX] API Gagal ({response.status_code}). Respon: {res_body}")
                self.after(0, self.add_history, f"MASTERBOX API ERROR ({response.status_code}) -> {res_body[:60]}")
        except Exception as e:
            logging.error(f"[MASTERBOX] Error Jaringan ke API Master Box: {e}")
            self.after(0, self.add_history, "[MASTERBOX] Jaringan API Gagal. Dipindah ke failed.")
            
        # Pindahkan file berdasarkan status sukses
        try:
            if success:
                dest = os.path.join(LOG_DIR_TIMBANGAN, "sent", file_name)
                shutil.move(file_path, dest)
            else:
                dest = os.path.join(LOG_DIR_TIMBANGAN, "failed", file_name)
                shutil.move(file_path, dest)
        except Exception as e_move:
            logging.error(f"[MASTERBOX] Gagal memindahkan file log: {e_move}")

    def reprint_masterbox(self):
        """Memanggil API Masterbox-retry untuk reprint Master Box terakhir"""
        if not PRINTER_ENABLE:
            return
        self.after(0, self.set_printer_status, "REPRINT MB: PROSES...", "#3b82f6", "Meminta data retry...")
        payload = {"line_no": str(TIMBANGAN_LINE_NO)}
        
        logging.info(f"[MASTERBOX] Mengirim POST request reprint ke {TIMBANGAN_RETRY_API_URL}")
        try:
            start_time = time.time()
            response = requests.post(TIMBANGAN_RETRY_API_URL, json=payload, timeout=8)
            duration = time.time() - start_time
            
            if response.status_code == 200:
                res_data = response.json()
                data = res_data.get("data", {})
                code = data.get("code", "MOCK.MB.CODE.ERROR")
                
                metadata = data.get("metaData", {})
                raw_part_code = metadata.get("part_code", "-")
                parts = [p.strip() for p in raw_part_code.split(" ") if p.strip()]
                if len(parts) >= 2:
                    part_code = parts[0]
                    batt_type = " ".join(parts[1:])
                else:
                    part_code = raw_part_code
                    batt_type = "-"
                
                # Parsing tanggal
                created_at_raw = data.get("createdAt", "")
                try:
                    dt_part = created_at_raw.split(".")[0]
                    dt = datetime.strptime(dt_part, "%Y-%m-%dT%H:%M:%S")
                    date_str = dt.strftime("%d-%b-%Y")
                except:
                    date_str = datetime.now().strftime("%d-%b-%Y")
                
                weight = metadata.get("weight", "0.0")
                quantity = metadata.get("quantity", "0")
                code_production = (
                    data.get("codeProduction") or 
                    data.get("code_production") or 
                    res_data.get("codeProduction") or 
                    res_data.get("code_production") or 
                    metadata.get("codeProduction") or 
                    metadata.get("code_production") or 
                    "-"
                )
                
                logging.info(f"[MASTERBOX] API Reprint Sukses ({response.status_code}) dalam {duration:.2f}s. Code: {code}, CodeProd: {code_production}")
                self.after(0, self.add_history, f"MASTERBOX REPRINT -> Sukses. QR: {code}")
                
                # Print Masterbox
                self.execute_physical_print_masterbox(
                    code=code,
                    part_code=part_code,
                    batt_type=batt_type,
                    weight=weight,
                    quantity=quantity,
                    date_str=date_str,
                    code_production=code_production
                )
                self.after(2000, lambda: self.reset_printer_visual_state())
            else:
                res_body = response.text.strip()
                logging.error(f"[MASTERBOX] API Reprint Gagal ({response.status_code}). Respon: {res_body}")
                self.after(0, self.add_history, f"MB REPRINT API ERROR ({response.status_code}) -> {res_body[:60]}")
                self.after(0, self.set_printer_status, "REPRINT GAGAL (API)", "#ef4444", f"Status: {response.status_code}")
                self.after(3000, lambda: self.reset_printer_visual_state())
        except Exception as e:
            logging.error(f"[MASTERBOX] Error Reprint Master Box: {e}")
            self.after(0, self.add_history, "[MASTERBOX] Jaringan API Reprint Gagal.")
            self.after(0, self.set_printer_status, "REPRINT GAGAL (NET)", "#ef4444", "Net Error")
            self.after(3000, lambda: self.reset_printer_visual_state())

    # --- WATCHER LOOP REALTIME (logs/ folder) ---
    def watcher_loop(self):
        """Memantau logs/ folder secara realtime menggunakan watchdog observer"""
        class LogHandler(FileSystemEventHandler):
            def __init__(self, app_instance):
                self.app = app_instance
                self.processed = set()
                
            def on_created(self, event):
                if not event.is_directory and event.src_path.endswith('.txt'):
                    file_name = os.path.basename(event.src_path)
                    if file_name.startswith('log_line_no_'):
                        self.process(event.src_path)
                        
            def process(self, file_path):
                if file_path in self.processed:
                    return
                self.processed.add(file_path)
                time.sleep(0.3) # Tunggu agar penulisan file selesai sempurna
                
                try:
                    payload = {}
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        
                    for line in lines:
                        line = line.strip()
                        if ':' not in line:
                            continue
                        key, val = line.split(':', 1)
                        key = key.strip()
                        val = val.strip()
                        
                        if key == "Line_No":
                            payload['line_no'] = val
                        elif key == "Recent_Weight":
                            try:
                                num = val.split()[0]
                                payload['weight'] = float(num)
                            except:
                                payload['weight'] = 0.0
                        elif key == "Recent_Qty":
                            try:
                                num = val.split()[0]
                                payload['quantity'] = int(num)
                            except:
                                payload['quantity'] = 0
                        elif key == "Product_Type":
                            # Bersihkan null bytes & hapus suffix tipe data seperti (STRING)
                            clean_val = val.replace('\x00', '').strip()
                            # Hapus suffix (STRING), (SHORT_STRING), dll di akhir
                            import re
                            clean_val = re.sub(r'\s*\([A-Z_]+\)\s*$', '', clean_val).strip()
                            payload['part_code'] = clean_val
                        elif key == "Timestamp":
                            try:
                                date_part = val[:8]
                                time_part = val[9:17]
                                day = date_part[0:2]
                                month = date_part[2:4]
                                year = date_part[4:8]
                                payload['timestamp'] = f"{year}-{month}-{day} {time_part}"
                            except:
                                payload['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                
                    if 'line_no' in payload and 'part_code' in payload and 'weight' in payload:
                        # Jalankan hit API & print di thread terpisah agar UI tidak hang
                        t = threading.Thread(
                            target=self.app.send_masterbox_api_and_print,
                            args=(payload, file_path),
                            daemon=True
                        )
                        t.start()
                    else:
                        logging.error(f"[MASTERBOX] Format file log {file_name} tidak valid.")
                        dest = os.path.join(LOG_DIR_TIMBANGAN, "error", os.path.basename(file_path))
                        shutil.move(file_path, dest)
                        
                except Exception as e:
                    logging.error(f"[MASTERBOX] Gagal membaca file log: {e}")
                    
        logging.info("[MASTERBOX] Watchdog Observer diaktifkan untuk logs/timbangan/...")
        handler = LogHandler(self)
        observer = Observer()
        observer.schedule(handler, LOG_DIR_TIMBANGAN, recursive=False)
        observer.start()
        
        # Proses file sisa yang mungkin belum terkirim saat startup
        try:
            for f_name in os.listdir(LOG_DIR_TIMBANGAN):
                if f_name.endswith('.txt') and f_name.startswith('log_line_no_'):
                    full_path = os.path.join(LOG_DIR_TIMBANGAN, f_name)
                    handler.process(full_path)
        except Exception as e_exist:
            logging.error(f"[MASTERBOX] Gagal memproses file startup: {e_exist}")
            
        while self.running:
            time.sleep(1)
        observer.stop()
        observer.join()

    def printer_rockwell_loop(self):
        logging.info(f"[PRINTER] Menghubungkan ke Rockwell {PRINTER_PLC_IP}...")
        self.after(0, self.set_printer_status, "MENGHUBUNGKAN...", "#f59e0b", "Connecting to Rockwell")
        try:
            plc = LogixDriver(PRINTER_PLC_IP)
            plc.open()
            self.after(0, self.set_printer_status, "PRINTER READY", "#22c55e", "Rockwell Terhubung")
            
            last_button_state = False
            is_pressing_button = False
            button_press_start_time = 0
            reprint_triggered = False
            press_count = 0
            button_released_pending = False
            
            while self.running:
                res = plc.read(PRINTER_MONITOR_ADDR)
                if res and res.value is not None:
                    # Depending on data type, it might be boolean or int
                    current_button_state = bool(res.value)
                    
                    # Press
                    if current_button_state and not last_button_state:
                        button_press_start_time = time.time()
                        is_pressing_button = True
                        reprint_triggered = False
                        logging.info(f"[PRINTER] Tombol cetak mulai ditekan pada {PRINTER_MONITOR_ADDR} (Rockwell)")
                        
                    # Long Press
                    if current_button_state and is_pressing_button:
                        press_duration = time.time() - button_press_start_time
                        if press_duration >= 5.0 and not reprint_triggered:
                            display_msg = f"PLC -> Tombol ({PRINTER_MONITOR_ADDR}) ditahan 5s! Memicu REPRINT Pallet."
                            logging.info(f"[PRINTER] {display_msg}")
                            self.after(0, self.add_history, display_msg)
                            threading.Thread(target=self.hit_api_pallet_and_print, args=(True,), daemon=True).start()
                            reprint_triggered = True
                            press_count = 0
                            button_released_pending = False
                            
                    # Release
                    if not current_button_state and last_button_state:
                        if is_pressing_button:
                            press_duration = time.time() - button_press_start_time
                            if press_duration < 3.0 and not reprint_triggered:
                                press_count += 1
                                button_released_pending = True
                            is_pressing_button = False
                            
                    # Pending press logic
                    if button_released_pending and not is_pressing_button:
                        if time.time() - button_press_start_time >= 3.0:
                            if press_count == 1:
                                display_msg = f"PLC -> Tombol ({PRINTER_MONITOR_ADDR}) ditekan 1x. Memicu CETAK BARU."
                                logging.info(f"[PRINTER] {display_msg}")
                                self.after(0, self.add_history, display_msg)
                                threading.Thread(target=self.hit_api_pallet_and_print, args=(False,), daemon=True).start()
                            press_count = 0
                            button_released_pending = False
                            
                    last_button_state = current_button_state
                time.sleep(0.1)
                
        except Exception as e:
            logging.error(f"[PRINTER] Rockwell Error: {e}")
            self.after(0, self.set_printer_status, "PLC TERPUTUS", "#ef4444", "Rockwell Gagal")
            time.sleep(3)
            if self.running:
                self.after(3000, lambda: threading.Thread(target=self.printer_rockwell_loop, daemon=True).start())

    # --- LOOP UTAMA PEMANTAUAN PLC GABUNGAN (DOWNTIME + TOMBOL CETAK PALLET) ---
    def plc_loop(self):
        logging.info(f"[PLC] Jembatan PLC loop terpadu aktif. Mode: {DOWNTIME_CONN_MODE}")
        
        while self.running:
            if DOWNTIME_CONN_MODE == "cx_programmer":
                if DOWNTIME_ENABLE:
                    self.after(0, self.set_plc_status, "MENGHUBUNGKAN PLC...", "#f59e0b", "Mencari CX-Programmer...")
                if PRINTER_ENABLE:
                    self.after(0, self.set_printer_status, "MENGHUBUNGKAN PLC...", "#f59e0b", "Mencari CX-Programmer...")
                    
                self.after(0, self.add_history, "PLC: Menghubungkan ke CX-Programmer...")
                logging.info("[PLC] Mencari window CX-Programmer...")
                
                try:
                    if not PYWINAUTO_AVAILABLE:
                        raise RuntimeError("pywinauto missing")
                    app = Application(backend="win32").connect(title_re=".*CX-Programmer.*")
                    main_window = app.window(title_re=".*CX-Programmer.*")
                    watch_window = main_window.child_window(title="Watch Window", class_name="AfxWnd42")
                    list_view = watch_window.child_window(class_name="SysListView32", found_index=0)
                    
                    logging.info("[PLC] Terkoneksi dengan Watch Window CX-Programmer!")
                    self.after(0, self.add_history, "PLC: Berhasil terkoneksi dengan Watch Window.")
                    
                    if DOWNTIME_ENABLE:
                        self.after(0, self.set_plc_status, "PLC TERHUBUNG (CX-PROG)", "#22c55e", "Monitoring Active")
                    if PRINTER_ENABLE:
                        self.reset_printer_visual_state()
                        
                    last_downtime_values = {}
                    last_button_state = "0"
                    button_press_start_time = 0.0
                    is_pressing_button = False
                    reprint_triggered = False
                    press_count = 0
                    last_release_time = 0.0
                    button_released_pending = False
                    tick_counter = 0
                    target_button_row = -1
                    
                    while self.running:
                        # Scan list_view item row mapping
                        if tick_counter % 15 == 0 or target_button_row == -1:
                            try:
                                item_count = list_view.item_count()
                                target_button_row = -1
                                for row in range(item_count):
                                    address = list_view.get_item(row, 2).text().strip()
                                    if address == PRINTER_MONITOR_ADDR:
                                        target_button_row = row
                                        break
                            except Exception:
                                break
                                
                        # Scan Downtime
                        if DOWNTIME_ENABLE and (tick_counter % 15 == 0):
                            try:
                                item_count = list_view.item_count()
                                for row in range(item_count):
                                    plc_name = list_view.get_item(row, 0).text().strip()
                                    symbol_name = list_view.get_item(row, 1).text().strip()
                                    if not symbol_name:
                                        continue
                                    address = list_view.get_item(row, 2).text().strip()
                                    value = list_view.get_item(row, 5).text().strip()
                                    comment = list_view.get_item(row, 7).text().strip()
                                    
                                    key = (plc_name, symbol_name, address)
                                    if key not in last_downtime_values or last_downtime_values[key] != value:
                                        status = "RUNNING" if value == "1" else "STOPPED"
                                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                        
                                        log_line = f"[{timestamp}] PLC: {plc_name} | Symbol: {symbol_name} | Address: {address} | Status: {status} | Comment: {comment}\n"
                                        with open(DOWNTIME_LOG_PATH, "a", encoding="utf-8") as f:
                                            f.write(log_line)
                                            
                                        display_msg = f"PLC -> {symbol_name} ({comment}) : {status}"
                                        logging.info(f"[DOWNTIME] {display_msg}")
                                        self.after(0, self.add_history, display_msg)
                                        
                                        api_dt_thread = threading.Thread(
                                            target=self.send_downtime_api,
                                            args=(symbol_name, address, status, comment, timestamp),
                                            daemon=True
                                        )
                                        api_dt_thread.start()
                                        
                                        last_downtime_values[key] = value
                                        self.after(0, lambda sn=symbol_name, st=status: self.plc_machine_state.set(f"Mesin: {sn} ({st})"))
                            except Exception:
                                break
                                
                        # Detect Button
                        if PRINTER_ENABLE and PRINTER_CONN_MODE == "cx_programmer" and target_button_row != -1:
                            try:
                                current_button_state = list_view.get_item(target_button_row, 5).text().strip()
                                
                                # Press
                                if current_button_state == "1" and last_button_state == "0":
                                    button_press_start_time = time.time()
                                    is_pressing_button = True
                                    reprint_triggered = False
                                    logging.info(f"[PRINTER] Tombol cetak mulai ditekan pada {PRINTER_MONITOR_ADDR}")
                                    
                                # Long Press
                                if current_button_state == "1" and is_pressing_button:
                                    press_duration = time.time() - button_press_start_time
                                    if press_duration >= 5.0 and not reprint_triggered:
                                        display_msg = f"PLC -> Tombol ({PRINTER_MONITOR_ADDR}) ditahan 5s! Memicu REPRINT Pallet."
                                        logging.info(f"[PRINTER] {display_msg}")
                                        self.after(0, self.add_history, display_msg)
                                        
                                        print_thread = threading.Thread(target=self.hit_api_pallet_and_print, args=(True,), daemon=True)
                                        print_thread.start()
                                        
                                        reprint_triggered = True
                                        press_count = 0
                                        button_released_pending = False
                                        
                                # Release
                                if current_button_state == "0" and last_button_state == "1":
                                    if is_pressing_button:
                                        press_duration = time.time() - button_press_start_time
                                        if press_duration < 5.0 and not reprint_triggered:
                                            press_count += 1
                                            last_release_time = time.time()
                                            button_released_pending = True
                                            logging.info(f"[PRINTER] Tombol dilepas singkat. press_count={press_count}")
                                            
                                        is_pressing_button = False
                                        reprint_triggered = False
                                        
                                last_button_state = current_button_state
                                
                                # Process click buffer
                                if button_released_pending:
                                    elapsed = time.time() - last_release_time
                                    if press_count >= 2:
                                        display_msg = f"PLC -> Tombol ({PRINTER_MONITOR_ADDR}) ditekan 2 kali! Memicu REPRINT Master Box."
                                        logging.info(f"[PRINTER] {display_msg}")
                                        self.after(0, self.add_history, display_msg)
                                        
                                        mb_reprint_thread = threading.Thread(target=self.reprint_masterbox, daemon=True)
                                        mb_reprint_thread.start()
                                        
                                        press_count = 0
                                        button_released_pending = False
                                    elif elapsed >= 0.45 and not is_pressing_button:
                                        display_msg = f"PLC -> Tombol ({PRINTER_MONITOR_ADDR}) ditekan 1 kali. Memicu CETAK normal Pallet."
                                        logging.info(f"[PRINTER] {display_msg}")
                                        self.after(0, self.add_history, display_msg)
                                        
                                        print_thread = threading.Thread(target=self.hit_api_pallet_and_print, args=(False,), daemon=True)
                                        print_thread.start()
                                        
                                        press_count = 0
                                        button_released_pending = False
                            except Exception:
                                break
                                
                        tick_counter += 1
                        time.sleep(0.04)
                except Exception as e:
                    logging.error(f"[PLC] GUI Scraping Error: {e}")
                    if DOWNTIME_ENABLE:
                        self.after(0, self.set_plc_status, "PLC TERPUTUS", "#ef4444", "CX-Programmer tertutup")
                    if PRINTER_ENABLE:
                        self.after(0, self.set_printer_status, "PLC TERPUTUS", "#ef4444", "CX-Programmer tertutup")
                    for _ in range(50):
                        if not self.running: break
                        time.sleep(0.1)
            else:
                # Mode Komunikasi Langsung: SERIAL HOST LINK atau ETHERNET FINS UDP
                if DOWNTIME_ENABLE:
                    self.after(0, self.set_plc_status, "MENGHUBUNGKAN PLC...", "#f59e0b", f"Connecting via {DOWNTIME_CONN_MODE}...")
                if PRINTER_ENABLE:
                    self.after(0, self.set_printer_status, "MENGHUBUNGKAN PLC...", "#f59e0b", f"Connecting via {DOWNTIME_CONN_MODE}...")
                
                self.after(0, self.add_history, f"PLC: Mencoba terhubung via {DOWNTIME_CONN_MODE}...")
                
                # Coba baca 1 register untuk test koneksi
                test_val = self.get_omron_address_value(DOWNTIME_CONN_MODE, DOWNTIME_PLC_IP, DOWNTIME_PLC_PORT, DOWNTIME_PLC_BAUD, PRINTER_MONITOR_ADDR)
                if test_val is None:
                    # Gagal koneksi
                    if DOWNTIME_ENABLE:
                        self.after(0, self.set_plc_status, "PLC DISCONNECTED", "#ef4444", "Koneksi Gagal")
                    if PRINTER_ENABLE:
                        self.after(0, self.set_printer_status, "PLC DISCONNECTED", "#ef4444", "Koneksi Gagal")
                    self.after(0, self.add_history, "PLC: Gagal menghubungi PLC. Cek IP/Port/Kabel.")
                    for _ in range(50):
                        if not self.running: break
                        time.sleep(0.1)
                    continue
                
                # Sukses Terhubung
                if DOWNTIME_ENABLE:
                    self.after(0, self.set_plc_status, "PLC TERHUBUNG (DIRECT)", "#22c55e", f"Active Mode: {DOWNTIME_CONN_MODE}")
                if PRINTER_ENABLE:
                    self.reset_printer_visual_state()
                    
                last_downtime_values = {}
                last_button_state = "0"
                button_press_start_time = 0.0
                is_pressing_button = False
                reprint_triggered = False
                press_count = 0
                last_release_time = 0.0
                button_released_pending = False
                tick_counter = 0
                
                while self.running:
                    # Scan Downtime (setiap 15 ticks ~ 0.6 detik)
                    if DOWNTIME_ENABLE and (tick_counter % 15 == 0):
                        for item in DOWNTIME_ADDRESSES:
                            sym_name = item["symbol"]
                            address = item["address"]
                            comment = item["comment"]
                            
                            val = self.get_omron_address_value(DOWNTIME_CONN_MODE, DOWNTIME_PLC_IP, DOWNTIME_PLC_PORT, DOWNTIME_PLC_BAUD, address)
                            if val is not None:
                                key = address
                                if key not in last_downtime_values or last_downtime_values[key] != val:
                                    status = "RUNNING" if val == "1" else "STOPPED"
                                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    
                                    log_line = f"[{timestamp}] PLC: Direct | Symbol: {sym_name} | Address: {address} | Status: {status} | Comment: {comment}\n"
                                    with open(DOWNTIME_LOG_PATH, "a", encoding="utf-8") as f:
                                        f.write(log_line)
                                        
                                    display_msg = f"PLC -> {sym_name} ({comment}) : {status}"
                                    logging.info(f"[DOWNTIME] {display_msg}")
                                    self.after(0, self.add_history, display_msg)
                                    
                                    api_dt_thread = threading.Thread(
                                        target=self.send_downtime_api,
                                        args=(sym_name, address, status, comment, timestamp),
                                        daemon=True
                                    )
                                    api_dt_thread.start()
                                    
                                    last_downtime_values[key] = val
                                    self.after(0, lambda sn=sym_name, st=status: self.plc_machine_state.set(f"Mesin: {sn} ({st})"))
                                    
                    # Scan Button (setiap tick ~ 40ms)
                    if PRINTER_ENABLE:
                        current_button_state = self.get_omron_address_value(DOWNTIME_CONN_MODE, DOWNTIME_PLC_IP, DOWNTIME_PLC_PORT, DOWNTIME_PLC_BAUD, PRINTER_MONITOR_ADDR)
                        if current_button_state is None:
                            # Jika pembacaan gagal, anggap terputus
                            break
                            
                        # Press
                        if current_button_state == "1" and last_button_state == "0":
                            button_press_start_time = time.time()
                            is_pressing_button = True
                            reprint_triggered = False
                            logging.info(f"[PRINTER] Tombol cetak mulai ditekan pada {PRINTER_MONITOR_ADDR}")
                            
                        # Long Press
                        if current_button_state == "1" and is_pressing_button:
                            press_duration = time.time() - button_press_start_time
                            if press_duration >= 5.0 and not reprint_triggered:
                                display_msg = f"PLC -> Tombol ({PRINTER_MONITOR_ADDR}) ditahan 5s! Memicu REPRINT Pallet."
                                logging.info(f"[PRINTER] {display_msg}")
                                self.after(0, self.add_history, display_msg)
                                
                                print_thread = threading.Thread(target=self.hit_api_pallet_and_print, args=(True,), daemon=True)
                                print_thread.start()
                                
                                reprint_triggered = True
                                press_count = 0
                                button_released_pending = False
                                
                        # Release
                        if current_button_state == "0" and last_button_state == "1":
                            if is_pressing_button:
                                press_duration = time.time() - button_press_start_time
                                if press_duration < 5.0 and not reprint_triggered:
                                    press_count += 1
                                    last_release_time = time.time()
                                    button_released_pending = True
                                    logging.info(f"[PRINTER] Tombol dilepas singkat. press_count={press_count}")
                                    
                                is_pressing_button = False
                                reprint_triggered = False
                                
                        last_button_state = current_button_state
                        
                        # Process click buffer
                        if button_released_pending:
                            elapsed = time.time() - last_release_time
                            if press_count >= 2:
                                display_msg = f"PLC -> Tombol ({PRINTER_MONITOR_ADDR}) ditekan 2 kali! Memicu REPRINT Master Box."
                                logging.info(f"[PRINTER] {display_msg}")
                                self.after(0, self.add_history, display_msg)
                                
                                mb_reprint_thread = threading.Thread(target=self.reprint_masterbox, daemon=True)
                                mb_reprint_thread.start()
                                
                                press_count = 0
                                button_released_pending = False
                            elif elapsed >= 0.45 and not is_pressing_button:
                                display_msg = f"PLC -> Tombol ({PRINTER_MONITOR_ADDR}) ditekan 1 kali. Memicu CETAK normal Pallet."
                                logging.info(f"[PRINTER] {display_msg}")
                                self.after(0, self.add_history, display_msg)
                                
                                print_thread = threading.Thread(target=self.hit_api_pallet_and_print, args=(False,), daemon=True)
                                print_thread.start()
                                
                                press_count = 0
                                button_released_pending = False
                                
                    tick_counter += 1
                    time.sleep(0.04)

    # --- LOOP UTAMA PEMANTAUAN TIMBANGAN FISIK (UNIVERSAL) ---
    def timbangan_loop(self):
        """Loop pembacaan PLC Rockwell / Omron Timbangan secara universal"""
        
        while self.running:
            self.after(0, self.set_timbangan_status, "MENGHUBUNGKAN PLC...", "#f59e0b", f"Connecting via {TIMBANGAN_CONN_MODE}...")
            
            # MODE 1: ROCKWELL (EIP)
            if TIMBANGAN_CONN_MODE == "rockwell":
                if not PYCOMM3_AVAILABLE:
                    self.after(0, self.set_timbangan_status, "MOCK / MOCK ONLY", "#06b6d4", "Simulasi Aktif")
                    logging.info("[TIMBANGAN] pycomm3 tidak ada. Standby mode simulasi.")
                    while self.running:
                        time.sleep(1)
                    continue
                    
                logging.info(f"[TIMBANGAN] Mencoba menghubungkan ke PLC Rockwell {TIMBANGAN_PLC_IP}...")
                try:
                    plc = LogixDriver(TIMBANGAN_PLC_IP)
                    plc.open()
                    self.after(0, self.set_timbangan_status, "TIMBANGAN READY", "#22c55e", "Rockwell Online")
                    self.after(0, self.add_history, f"Timbangan: Terhubung ke PLC Rockwell {TIMBANGAN_PLC_IP}.")
                    
                    last_box = None
                    local_counter = 0
                    tags = [TIMBANGAN_TAG_WEIGHT, TIMBANGAN_TAG_QTY, TIMBANGAN_TAG_TYPE, TIMBANGAN_TAG_TOTALIZER]
                    
                    while self.running:
                        results = plc.read(*tags)
                        if results is None: raise RuntimeError("Data read error")
                        current_values = {r.tag: r.value for r in results}
                        
                        # Bersihkan null bytes dari string PLC Rockwell
                        for k, v in current_values.items():
                            if isinstance(v, str):
                                current_values[k] = v.replace('\x00', '').strip()
                        
                        current_box = current_values.get(TIMBANGAN_TAG_TOTALIZER)
                        if current_box is None: raise RuntimeError("Totalizer not found")
                        
                        if last_box is not None and current_box == last_box:
                            time.sleep(0.25)
                            continue
                            
                        local_counter += 1
                        last_box = current_box
                        
                        now = datetime.now()
                        time_full = now.strftime("%d%m%Y %H:%M:%S")
                        timestamp_file = now.strftime("%d%m%Y_%H%M%S")
                        
                        filename = os.path.join(LOG_DIR_TIMBANGAN, f"log_line_no_{TIMBANGAN_LINE_NO}_{timestamp_file}.txt")
                        lines = [
                            f"ID: {local_counter}",
                            f"Line_No : {TIMBANGAN_LINE_NO}",
                            f"Recent_Weight: {current_values.get(TIMBANGAN_TAG_WEIGHT, 0.0)} (REAL)",
                            f"Recent_Qty: {current_values.get(TIMBANGAN_TAG_QTY, 0)} (DINT)",
                            f"Product_Type: {current_values.get(TIMBANGAN_TAG_TYPE, '-')} (STRING)",
                            f"Timestamp: {time_full}",
                            "----------------------------------------"
                        ]
                        with open(filename, "w", encoding="utf-8") as f:
                            for l in lines: f.write(l + "\n")
                            
                        msg = f"Timbangan: Box Baru #{local_counter} ditimbang ({current_values.get(TIMBANGAN_TAG_WEIGHT, 0.0)} KG)"
                        self.after(0, self.add_history, msg)
                        logging.info(f"[TIMBANGAN] {msg}")
                        time.sleep(0.25)
                except Exception as e:
                    logging.error(f"[TIMBANGAN] Rockwell Error: {e}")
                    self.after(0, self.set_timbangan_status, "TIMBANGAN DISCONNECTED", "#ef4444", "Gagal Terhubung")
                    for _ in range(50):
                        if not self.running: break
                        time.sleep(0.1)
                        
            # MODE 2: OMRON (SERIAL / ETHERNET / CX-PROGRAMMER)
            else:
                # Membaca timbangan via Omron FINS/HostLink/CX-Programmer
                logging.info(f"[TIMBANGAN] Mencoba membaca PLC Omron via {TIMBANGAN_CONN_MODE}...")
                
                # Test koneksi dengan membaca register totalizer
                test_val = self.get_omron_address_value(TIMBANGAN_CONN_MODE, TIMBANGAN_PLC_IP, TIMBANGAN_PLC_PORT, TIMBANGAN_PLC_BAUD, TIMBANGAN_TAG_TOTALIZER)
                if test_val is None:
                    self.after(0, self.set_timbangan_status, "TIMBANGAN DISCONNECTED", "#ef4444", "PLC Omron Gagal")
                    for _ in range(50):
                        if not self.running: break
                        time.sleep(0.1)
                    continue
                    
                self.after(0, self.set_timbangan_status, "TIMBANGAN READY", "#22c55e", f"Omron ({TIMBANGAN_CONN_MODE})")
                self.after(0, self.add_history, f"Timbangan: Terhubung ke PLC Omron via {TIMBANGAN_CONN_MODE}.")
                
                last_box = None
                local_counter = 0
                
                while self.running:
                    try:
                        # 1. Baca register totalizer box
                        current_box_str = self.get_omron_address_value(TIMBANGAN_CONN_MODE, TIMBANGAN_PLC_IP, TIMBANGAN_PLC_PORT, TIMBANGAN_PLC_BAUD, TIMBANGAN_TAG_TOTALIZER)
                        if current_box_str is None: raise RuntimeError("Read error")
                        current_box = int(current_box_str)
                        
                        if last_box is not None and current_box == last_box:
                            time.sleep(0.3)
                            continue
                            
                        # 2. Box baru terdeteksi! Ambil seluruh data timbangan
                        weight_str = self.get_omron_address_value(TIMBANGAN_CONN_MODE, TIMBANGAN_PLC_IP, TIMBANGAN_PLC_PORT, TIMBANGAN_PLC_BAUD, TIMBANGAN_TAG_WEIGHT)
                        qty_str = self.get_omron_address_value(TIMBANGAN_CONN_MODE, TIMBANGAN_PLC_IP, TIMBANGAN_PLC_PORT, TIMBANGAN_PLC_BAUD, TIMBANGAN_TAG_QTY)
                        
                        # Membaca product type (biasanya string 20 char, dibaca 10 word)
                        part_code = "-"
                        area_type, word, bit = parse_omron_address(TIMBANGAN_TAG_TYPE)
                        if area_type is not None:
                            if TIMBANGAN_CONN_MODE == "serial":
                                words = OmronPLCHelper.read_words_serial(TIMBANGAN_PLC_PORT, TIMBANGAN_PLC_BAUD, area_type, word, 10)
                                if words: part_code = words_to_ascii(words)
                            elif TIMBANGAN_CONN_MODE == "ethernet":
                                words = OmronPLCHelper.read_words_fins_udp(TIMBANGAN_PLC_IP, 9600, area_type, word, 10)
                                if words: part_code = words_to_ascii(words)
                        
                        # Parsing tipe data numerik
                        weight = float(weight_str) if weight_str else 0.0
                        # Biasanya data berat di Omron dikirim dalam integer skala (misal 1544 = 15.44 KG), bagi 100 jika berupa nilai integer besar > 200
                        if weight > 200:
                            weight = weight / 100.0
                            
                        qty = int(qty_str) if qty_str else 0
                        
                        local_counter += 1
                        last_box = current_box
                        
                        now = datetime.now()
                        time_full = now.strftime("%d%m%Y %H:%M:%S")
                        timestamp_file = now.strftime("%d%m%Y_%H%M%S")
                        
                        filename = os.path.join(LOG_DIR_TIMBANGAN, f"log_line_no_{TIMBANGAN_LINE_NO}_{timestamp_file}.txt")
                        lines = [
                            f"ID: {local_counter}",
                            f"Line_No : {TIMBANGAN_LINE_NO}",
                            f"Recent_Weight: {weight} (REAL)",
                            f"Recent_Qty: {qty} (DINT)",
                            f"Product_Type: {part_code} (STRING)",
                            f"Timestamp: {time_full}",
                            "----------------------------------------"
                        ]
                        with open(filename, "w", encoding="utf-8") as f:
                            for l in lines: f.write(l + "\n")
                            
                        msg = f"Timbangan: Box Baru #{local_counter} ditimbang ({weight} KG)"
                        self.after(0, self.add_history, msg)
                        logging.info(f"[TIMBANGAN] {msg}")
                        
                        time.sleep(0.3)
                    except Exception as e_loop:
                        logging.error(f"[TIMBANGAN] Omron read error: {e_loop}")
                        break

    def start_http_server(self):
        port = HTTP_PORT
        PrintRequestHandler.app_instance = self
        try:
            self.http_server = HTTPServer(('0.0.0.0', port), PrintRequestHandler)
            logging.info(f"[HTTP-SERVER] Server berjalan di http://0.0.0.0:{port}")
            self.http_server.serve_forever()
        except Exception as e:
            logging.error(f"[HTTP-SERVER] Gagal memulai server HTTP: {e}")

    def on_close(self):
        logging.info("Menutup aplikasi...")
        self.running = False
        if hasattr(self, 'http_server'):
            try:
                self.http_server.shutdown()
                logging.info("[HTTP-SERVER] Server dihentikan dengan sukses.")
            except Exception as e:
                logging.error(f"[HTTP-SERVER] Gagal menghentikan server: {e}")
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.destroy()

if __name__ == "__main__":
    app = ScannerApp()
    app.mainloop()
