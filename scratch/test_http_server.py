import threading
import time
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class TestRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[HTTP] {format%args}")

    def do_GET(self):
        if self.path == '/status':
            self.send_response_json({"status": "running"})
        elif self.path == '/print':
            print("PRINT REQUEST SIMULATED!")
            self.send_response_json({"status": "success", "message": "Printed"})
        else:
            self.send_response_json({"status": "error", "message": "Not Found"}, 404)

    def send_response_json(self, data, status_code=200):
        response_bytes = json.dumps(data).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

def start_server():
    server = HTTPServer(('127.0.0.1', 9999), TestRequestHandler)
    print("Server starting...")
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server

if __name__ == "__main__":
    srv = start_server()
    time.sleep(1)
    
    # Hit /status
    print("Testing GET /status...")
    r = requests.get("http://127.0.0.1:9999/status")
    print(f"Status response: {r.status_code} - {r.text}")
    
    # Hit /print
    print("Testing GET /print...")
    r = requests.get("http://127.0.0.1:9999/print")
    print(f"Print response: {r.status_code} - {r.text}")
    
    print("Shutting down server...")
    srv.shutdown()
    print("Server stopped successfully!")
