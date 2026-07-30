import requests
import json
import time
from datetime import datetime

line_no = "1"
pack_codes = [
    "YBID2607M21A0206A",
    "YBID2607M21A0207A",
    "YBID2607M21A0208A",
    "YBID2607M21A0209A",
    "YBID2607M21A0210A",
    "YBID2607M21A0211A"
]

print("=== STEP 1: SCANNING 6 FINISHED GOODS CODES ON LINE 1 ===")
for code in pack_codes:
    url_scan = "https://api.pms.yuasa.seavihive.com/api/fix-scanner"
    payload_scan = {
        "line_no": line_no,
        "pack_code": code
    }
    try:
        response = requests.post(url_scan, json=payload_scan, timeout=10)
        print(f"Scanned {code} -> Status: {response.status_code}, Respon: {response.text.strip()}")
    except Exception as e:
        print(f"Failed scanning {code}: {e}")
    time.sleep(0.5)

print("\n=== STEP 2: SUBMITTING TIMBANGAN (MASTER BOX) ON LINE 1 ===")
url_timbangan = "https://api.pms.yuasa.seavihive.com/api/fix-scanner-masterbox"
payload_timbangan = {
    "line_no": line_no,
    "part_code": "M221SDCAC20 B.CH-YTZ5S (Wet-CF) YU-5",
    "weight": 15.44,
    "quantity": 6,
    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}
try:
    response = requests.post(url_timbangan, json=payload_timbangan, timeout=10)
    print(f"Status Code: {response.status_code}")
    if response.status_code in [200, 201]:
        res_json = response.json()
        print("Master Box Response:")
        print(json.dumps(res_json, indent=4))
    else:
        print(f"Error Response: {response.text}")
except Exception as e:
    print(f"Timbangan request failed: {e}")

print("\n=== STEP 3: SUBMITTING PALLET PRINT REQUEST ON LINE 1 ===")
url_pallet = "https://api.pms.yuasa.seavihive.com/api/fix-scanner-pallet"
payload_pallet = {
    "line_no": line_no
}
try:
    response = requests.post(url_pallet, json=payload_pallet, timeout=10)
    print(f"Status Code: {response.status_code}")
    if response.status_code in [200, 201]:
        res_json = response.json()
        print("Pallet Response:")
        print(json.dumps(res_json, indent=4))
    else:
        print(f"Error Response: {response.text}")
except Exception as e:
    print(f"Pallet request failed: {e}")
