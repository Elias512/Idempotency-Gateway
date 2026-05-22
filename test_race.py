import threading
import requests

URL = "http://127.0.0.1:8000/process-payment"
HEADERS = {"idempotency-key": "race-test-key-001"}
BODY = {"amount": 100, "currency": "GHS"}


def send_request(request_number):
    response = requests.post(URL, json=BODY, headers=HEADERS)
    print(f"Request {request_number}: Status={response.status_code}")
    print(f"Request {request_number}: Response={response.json()}")
    print(
        f"Request {request_number}: X-Cache-Hit={response.headers.get('X-Cache-Hit', 'false')}"
    )
    print("---")


# Send 2 requests at the exact same time
thread1 = threading.Thread(target=send_request, args=(1,))
thread2 = threading.Thread(target=send_request, args=(2,))

thread1.start()
thread2.start()

thread1.join()
thread2.join()
