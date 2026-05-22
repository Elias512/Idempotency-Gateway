from fastapi import FastAPI, Header, HTTPException, Response
from pydantic import BaseModel
import time
import hashlib
import json
import threading

# Creating the FastAPI application
app = FastAPI()

# The notebook to store all processed payments
storage = {}

# Tracking keys that are currently being processed
in_flight = {}

# A lock to prevent race conditions
lock = threading.Lock()

# Defining how the payment request should look like
class PaymentRequest(BaseModel):
    amount: float
    currency: str

def hash_body(payment: PaymentRequest):
    # Converting the payment body into a unique fingerprint
    body_str = json.dumps(payment.dict(), sort_keys=True)
    return hashlib.md5(body_str.encode()).hexdigest()

@app.post("/process-payment")
def process_payment(
    payment: PaymentRequest,
    idempotency_key: str = Header(...),
    response: Response = None
):
    body_hash = hash_body(payment)

    with lock:
        # CASE 1: If the key has been seen before
        if idempotency_key in storage:
            stored = storage[idempotency_key]

            # CASE 2: Same key but DIFFERENT body - rejecting the request
            if stored["body_hash"] != body_hash:
                raise HTTPException(
                    status_code = 409,
                    detail = "Idempotency key already used for a different request body."
                )
            
            # CASE 3: Same key, same body - return saved response
            response.headers["X-Cache-Hit"] = "true"
            return stored["response"]
        
        # CASE 4: Key is currently being processed in-flight
        if idempotency_key in in_flight :
            event = in_flight[idempotency_key]
            should_process = False
        else :
            # CASE 5: Brand new key, creating an event and start processing
            event = threading.Event()
            in_flight[idempotency_key] = event
            should_process = True

    # If another request is already processing this key, wait for it 
    if not should_process :
        event.wait(timeout = 30)

        # Returning the result after waiting
        with lock :
            if idempotency_key in storage :
                response.headers["X-Cache-Hit"] = "true"
                return storage[idempotency_key]["response"]
            else :
                raise HTTPException(
                    status_code = 500,
                    detail = "Processing took too long. Please try again."
                )

    # Processing the brand new payment
    try :
        time.sleep(2)

        result = {
            "status" : "success",
            "message" : f"Charged {payment.amount} {payment.currency}"
        }

        # Storing the result in the notebook with the key and body hash
        with lock :
            storage[idempotency_key] = {
                "body_hash" : body_hash,
                "response" : result
            }
    finally :
        # Always signal waiting requests, even if something goes wrong
        with lock :
            if idempotency_key in in_flight :
                del in_flight[idempotency_key]
        event.set()

    return result
