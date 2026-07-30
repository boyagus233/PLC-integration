import os
import json
import time
import shutil
import logging
import threading
import requests
from datetime import datetime
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ========================================
# CONFIGURATION
# ========================================
WATCH_FOLDER = "logs"
SENT_FOLDER = "logs/sent"
ERROR_FOLDER = "logs/error"
FAILED_FOLDER = "logs/failed"
API_URL = "https://api.pms.yuasa.seavihive.com/api/fix-scanner-masterbox"
LOG_FILE = "monitor.log"
HEARTBEAT_FILE = "heartbeat.txt"

# Retry configuration
MAX_RETRIES = 5
RETRY_DELAY = 60  # seconds
API_TIMEOUT = 30  # seconds

# Create all folders
for folder in [WATCH_FOLDER, SENT_FOLDER, ERROR_FOLDER, FAILED_FOLDER]:
    Path(folder).mkdir(parents=True, exist_ok=True)

# ========================================
# LOGGING SETUP
# ========================================
class ProductionLogger:
    """Custom logger with rotation and dual output"""
    def __init__(self, log_file):
        self.log_file = log_file
        self.max_size_mb = 10
        
        # Create logger
        self.logger = logging.getLogger('PLC_Monitor')
        self.logger.setLevel(logging.DEBUG)
        
        # Clear existing handlers
        self.logger.handlers = []
        
        # File handler (UTF-8)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # Console handler (ASCII only - no emoji)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Check log rotation on startup
        self.rotate_if_needed()
    
    def rotate_if_needed(self):
        """Rotate log file if too large"""
        if os.path.exists(self.log_file):
            size_mb = os.path.getsize(self.log_file) / (1024 * 1024)
            if size_mb > self.max_size_mb:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup = f"{self.log_file}.{timestamp}.bak"
                shutil.move(self.log_file, backup)
                self.logger.info(f"Log rotated: {backup}")
    
    def info(self, msg):
        self.logger.info(msg)
    
    def warning(self, msg):
        self.logger.warning(msg)
    
    def error(self, msg):
        self.logger.error(msg)
    
    def critical(self, msg):
        self.logger.critical(msg)
    
    def debug(self, msg):
        self.logger.debug(msg)

logger = ProductionLogger(LOG_FILE)

# ========================================
# FILE PROCESSOR
# ========================================
class FileProcessor:
    def __init__(self):
        self.last_file = None
        self.processed_count = 0
        self.failed_count = 0
    
    def process_file(self, file_path):
        """Process a single file and send to API"""
        file_name = os.path.basename(file_path)
        
        # Prevent duplicate processing
        if self.last_file == file_path:
            logger.debug(f"Skipping duplicate: {file_name}")
            return
        
        self.last_file = file_path
        logger.info(f"[PROCESS] Processing: {file_name}")
        start_time = time.time()
        
        try:
            # Wait for file to be fully written
            time.sleep(0.3)
            
            # Read file with retry
            content = self._read_file_with_retry(file_path)
            if not content:
                self._move_to_error(file_path, "Cannot read file")
                return
            
            # Parse data
            data = self._parse_data(content)
            if not data:
                self._move_to_error(file_path, "Invalid data format")
                return
            
            # Validate required fields
            required = ['line_no', 'part_code', 'weight', 'quantity']
            missing = [f for f in required if f not in data]
            if missing:
                self._move_to_error(file_path, f"Missing fields: {missing}")
                return
            
            # Parse timestamp
            data = self._parse_timestamp(data)
            
            # Build payload
            payload = {
                'line_no': data['line_no'],
                'part_code': data['part_code'],
                'weight': data['weight'],
                'timestamp': data['timestamp'],
                'quantity': data['quantity']
            }
            
            logger.info(f"[SEND] Sending: {json.dumps(payload)}")
            
            # Send with retry
            success = self._send_with_retry(payload)
            
            elapsed = (time.time() - start_time) * 1000
            
            if success:
                self._move_to_sent(file_path)
                self.processed_count += 1
                logger.info(f"[SUCCESS] {file_name} ({elapsed:.0f}ms) [Total: {self.processed_count}]")
            else:
                self._move_to_failed(file_path)
                self.failed_count += 1
                logger.error(f"[FAILED] {file_name} [Total failed: {self.failed_count}]")
                
        except Exception as e:
            logger.error(f"[ERROR] Processing {file_name}: {e}")
            self._move_to_error(file_path, str(e))
    
    def _read_file_with_retry(self, file_path, max_attempts=5):
        """Read file with retry on lock"""
        for attempt in range(max_attempts):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.readlines()
            except (IOError, PermissionError) as e:
                if attempt < max_attempts - 1:
                    time.sleep(0.2)
                    continue
                logger.error(f"Cannot read file after {max_attempts} attempts: {e}")
                return None
        return None
    
    def _parse_data(self, lines):
        """Parse log file data"""
        data = {}
        for line in lines:
            line = line.strip()
            if ':' not in line:
                continue
            
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            
            if key == "Line_No":
                data['line_no'] = value
            elif key == "Recent_Weight":
                try:
                    # Extract number from "12.25 (REAL)"
                    num = value.split()[0]
                    data['weight'] = float(num)
                except:
                    data['weight'] = 0.0
            elif key == "Recent_Qty":
                try:
                    num = value.split()[0]
                    data['quantity'] = int(num)
                except:
                    data['quantity'] = 0
            elif key == "Product_Type":
                data['part_code'] = value
            elif key == "Timestamp":
                data['timestamp_raw'] = value
        
        return data
    
    def _parse_timestamp(self, data):
        """Parse timestamp from DDMMYYYY HH:MM:SS to YYYY-MM-DD HH:MM:SS"""
        if 'timestamp_raw' in data:
            try:
                ts = data['timestamp_raw']
                # Format: 12042026 11:05:17
                date_part = ts[:8]  # DDMMYYYY
                time_part = ts[9:17]  # HH:MM:SS
                
                day = date_part[0:2]
                month = date_part[2:4]
                year = date_part[4:8]
                
                data['timestamp'] = f"{year}-{month}-{day} {time_part}"
                del data['timestamp_raw']
            except Exception as e:
                logger.warning(f"Invalid timestamp format, using current time: {e}")
                data['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        else:
            data['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return data
    
    def _send_with_retry(self, payload):
        """Send payload to API with retry mechanism"""
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = requests.post(
                    API_URL,
                    json=payload,
                    timeout=API_TIMEOUT,
                    headers={'Content-Type': 'application/json'}
                )
                
                if response.status_code in [200, 201]:
                    logger.info(f"[API] Success (attempt {attempt}/{MAX_RETRIES})")
                    return True
                
                # Check if should retry
                status_code = response.status_code
                if 400 <= status_code < 500 and status_code != 429:
                    # Client error (except 429), don't retry
                    logger.error(f"[API] Client error {status_code}, not retrying")
                    return False
                
                logger.warning(f"[API] HTTP {status_code}: {response.text[:100]}")
                
            except requests.exceptions.Timeout:
                logger.warning(f"[API] Timeout (attempt {attempt}/{MAX_RETRIES})")
            except requests.exceptions.ConnectionError:
                logger.warning(f"[API] Connection error (attempt {attempt}/{MAX_RETRIES})")
            except Exception as e:
                logger.warning(f"[API] Error (attempt {attempt}/{MAX_RETRIES}): {e}")
            
            if attempt < MAX_RETRIES:
                logger.info(f"[RETRY] Waiting {RETRY_DELAY}s before retry...")
                time.sleep(RETRY_DELAY)
        
        logger.error(f"[API] Failed after {MAX_RETRIES} attempts")
        return False
    
    def _move_file(self, src, dest_folder, new_name=None):
        """Move file to destination folder"""
        try:
            if new_name is None:
                new_name = os.path.basename(src)
            dest_path = os.path.join(dest_folder, new_name)
            shutil.move(src, dest_path)
            return True
        except Exception as e:
            logger.error(f"Failed to move file: {e}")
            return False
    
    def _move_to_sent(self, file_path):
        """Move to sent folder"""
        self._move_file(file_path, SENT_FOLDER)
    
    def _move_to_error(self, file_path, reason=""):
        """Move to error folder"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = os.path.basename(file_path)
        new_name = f"{os.path.splitext(file_name)[0]}_{timestamp}.txt"
        self._move_file(file_path, ERROR_FOLDER, new_name)
        if reason:
            logger.error(f"[ERROR] {file_name} - {reason}")
    
    def _move_to_failed(self, file_path):
        """Move to failed folder with timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = os.path.basename(file_path)
        new_name = f"{os.path.splitext(file_name)[0]}_{timestamp}.txt"
        self._move_file(file_path, FAILED_FOLDER, new_name)
        logger.error(f"[FAILED] Moved to failed: {file_name}")

# ========================================
# WATCHER HANDLER
# ========================================
class FileHandler(FileSystemEventHandler):
    def __init__(self, processor):
        self.processor = processor
        self.processing = set()  # Track files being processed
    
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.txt'):
            self._handle_file(event.src_path)
    
    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('.txt'):
            # Only process if not already processing
            if event.src_path not in self.processing:
                self._handle_file(event.src_path)
    
    def _handle_file(self, file_path):
        """Handle file with deduplication"""
        if file_path in self.processing:
            logger.debug(f"Skipping already processing: {os.path.basename(file_path)}")
            return
        
        self.processing.add(file_path)
        try:
            self.processor.process_file(file_path)
        finally:
            self.processing.discard(file_path)

# ========================================
# HEARTBEAT MONITOR
# ========================================
def heartbeat_loop():
    """Write heartbeat every 30 seconds"""
    while True:
        try:
            with open(HEARTBEAT_FILE, 'w') as f:
                f.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            time.sleep(30)
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
            time.sleep(30)

# ========================================
# PROCESS EXISTING FILES
# ========================================
def process_existing_files(processor):
    """Process any existing files on startup"""
    try:
        files = [f for f in os.listdir(WATCH_FOLDER) 
                if f.endswith('.txt') and os.path.isfile(os.path.join(WATCH_FOLDER, f))]
        
        if files:
            logger.info(f"[STARTUP] Found {len(files)} existing files")
            for file in sorted(files):
                file_path = os.path.join(WATCH_FOLDER, file)
                processor.process_file(file_path)
    except Exception as e:
        logger.error(f"Error processing existing files: {e}")

# ========================================
# MAIN
# ========================================
def main():
    logger.info("=" * 60)
    logger.info("PLC FILE MONITOR STARTED (PRODUCTION)")
    logger.info("=" * 60)
    logger.info(f"Watch Folder:  {os.path.abspath(WATCH_FOLDER)}")
    logger.info(f"Sent Folder:   {os.path.abspath(SENT_FOLDER)}")
    logger.info(f"Error Folder:  {os.path.abspath(ERROR_FOLDER)}")
    logger.info(f"Failed Folder: {os.path.abspath(FAILED_FOLDER)}")
    logger.info(f"Log File:      {os.path.abspath(LOG_FILE)}")
    logger.info(f"API URL:       {API_URL}")
    logger.info("=" * 60)
    
    # Create processor
    processor = FileProcessor()
    
    # Process existing files first
    process_existing_files(processor)
    
    # Start heartbeat in background
    heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
    heartbeat_thread.start()
    logger.info("[HEARTBEAT] Started")
    
    # Start file watcher
    event_handler = FileHandler(processor)
    observer = Observer()
    observer.schedule(event_handler, WATCH_FOLDER, recursive=False)
    observer.start()
    logger.info("[WATCHER] Started (REALTIME)")
    logger.info("=" * 60)
    logger.info("Service is running. Press Ctrl+C to stop.")
    logger.info("=" * 60)
    
    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping service...")
        observer.stop()
        observer.join()
        logger.info("Service stopped")

if __name__ == "__main__":
    main()