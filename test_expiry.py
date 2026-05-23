import requests
import time

URL = "http://127.0.0.1:8000/process-payment"
HEADERS = {"idempotency-key": "expiry-test-key-003"}
BODY = {"amount": 100, "currency": "GHS"}

print("Sending first request...")
response1 = requests.post(URL, json=BODY, headers=HEADERS)
print(f"Response 1: {response1.json()}")
print(f"X-Cache-Hit: {response1.headers.get('X-Cache-Hit', 'false')}")
print("---")

print("Waiting 5 seconds for key to expire...")
time.sleep(5)

print("Sending second request with same key after expiry...")
response2 = requests.post(URL, json=BODY, headers=HEADERS)
print(f"Status Code: {response2.status_code}")
print(f"Raw Response: {response2.text}")
print("---")
