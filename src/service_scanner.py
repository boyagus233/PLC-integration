import os
import sys
import time
import signal
import logging

# Pastikan flag --service selalu ada saat dijalankan lewat service
if '--service' not in sys.argv:
    sys.argv.append('--service')

# Tambahkan path src ke sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
PARENT_DIR = os.path.dirname(SCRIPT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

import read_scanner_gui

def config_monitor_thread(app_instance, config_file):
    """Memantau apakah config.ini diubah di lapangan, dan mencatatnya ke log"""
    if not os.path.exists(config_file):
        return
    try:
        last_mtime = os.path.getmtime(config_file)
        while app_instance.running:
            time.sleep(5)
            if os.path.exists(config_file):
                current_mtime = os.path.getmtime(config_file)
                if current_mtime > last_mtime:
                    last_mtime = current_mtime
                    logging.info(f"[CONFIG-WATCHER] Terdeteksi perubahan pada '{config_file}'!")
                    logging.info("[CONFIG-WATCHER] Jika Anda mengubah PORT, IP, atau LINE_NO, silakan jalankan shortcut 'Restart Service' di Desktop.")
    except Exception as e:
        logging.error(f"[CONFIG-WATCHER] Error monitor config: {e}")

def main():
    logging.info("========================================================")
    logging.info("  YUASA INDUSTRIAL SCANNER & PLC BRIDGE (WINDOWS SERVICE)")
    logging.info("========================================================")
    
    # Inisialisasi aplikasi ScannerApp dalam mode headless
    app = read_scanner_gui.ScannerApp()
    
    # Graceful shutdown handler
    def handle_signal(sig, frame):
        logging.info(f"[SERVICE] Menerima sinyal terminasi ({sig}). Menghentikan service secara aman...")
        app.on_close()
        sys.exit(0)
        
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    # Jalankan monitor perubahan config.ini
    import threading
    config_file = os.path.join(read_scanner_gui.BASE_DIR, "config.ini")
    t_cfg = threading.Thread(target=config_monitor_thread, args=(app, config_file), daemon=True)
    t_cfg.start()
    
    logging.info("[SERVICE] Service aktif dan siap memproses data 24/7.")
    app.mainloop()

if __name__ == "__main__":
    main()
