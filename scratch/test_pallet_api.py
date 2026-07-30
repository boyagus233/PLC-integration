import requests
import json

url = "https://api.pms.yuasa.seavihive.com/api/fix-scanner-pallet"
payload = {"line_no": "14"}

try:
    print(f"Sending request to {url} with payload {payload}...")
    response = requests.post(url, json=payload, timeout=10)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        res_json = response.json()
        print("Response JSON:")
        print(json.dumps(res_json, indent=4))
    else:
        print(f"Error Response text: {response.text}")
except Exception as e:
    print(f"Request failed: {e}")
