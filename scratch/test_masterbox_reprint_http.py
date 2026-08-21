import requests
import json

# Test local HTTP server endpoint
url = "http://127.0.0.1:8080/reprint-masterbox"
payload = {
    "line_no": 14,
    "pack_code": "YBID.MB.260805.14.000002"
}

print(f"[*] Sending POST request to {url} with payload: {payload}")
try:
    res = requests.post(url, json=payload, timeout=3)
    print(f"[+] Status Code: {res.status_code}")
    print(f"[+] Response JSON: {res.json()}")
except Exception as e:
    print(f"[-] Error: {e}")
