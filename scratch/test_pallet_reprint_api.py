import requests
import json

url_pallet_retry = "https://api.pms.yuasa.seavihive.com/api/fix-scanner-pallet-retry"
payload = {"line_no": "1"}

print("Hitting Pallet Retry API for Line 1...")
try:
    res = requests.post(url_pallet_retry, json=payload, timeout=10)
    print(f"Status Code: {res.status_code}")
    if res.status_code in [200, 201]:
        print("Pallet Retry Response:")
        print(json.dumps(res.json(), indent=4))
    else:
        print("Error response:", res.text)
except Exception as e:
    print("Error:", e)
