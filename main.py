from fastapi import FastAPI, Header, HTTPException, Response
from pydantic import BaseModel
import time
import hashlib
import json
import threading
from datetime import datetime, timedelta

# Creating the FastAPI application
app = FastAPI()

# The notebook to store all processed payments
storage = {}

# Tracking keys that are currently being processed
in_flight = {}

# A lock to prevent race conditions
lock = threading.Lock()

# Key expiry duration (24 hours) .Programmers Feature
KEY_EXPIRY_HOURS = 24 # Testing purposes - set to 0.001 instead of 24 to test expiry logic

# Defining how the payment request should look like
class PaymentRequest(BaseModel):
    amount: float
    currency: str

    def validate_amount(self) :
        if self.amount <= 0 :
            raise HTTPException(
                status_code = 422,
                detail = "Amount must be greater than zero."
            )

def hash_body(payment: PaymentRequest):
    # Converting the payment body into a unique fingerprint
    body_str = json.dumps(payment.dict(), sort_keys=True)
    return hashlib.md5(body_str.encode()).hexdigest()

# Checking if a key has been stored for more than 24 hours
def is_expired(timestamp):
    return datetime.now() - timestamp > timedelta(hours = KEY_EXPIRY_HOURS)

@app.post("/process-payment")
def process_payment(
    payment: PaymentRequest,
    idempotency_key: str = Header(...),
    response: Response = None
):
    # Validate the payment amount
    payment.validate_amount()

    # Validate idempotency key
    if not idempotency_key or not idempotency_key.strip() :
        raise HTTPException(
            status_code= 400,
            detail = "Idempotency key is required and cannot be empty."
        )

    body_hash = hash_body(payment)

    with lock:
        # CASE 1: If the key has been seen before
        if idempotency_key in storage:
            stored = storage[idempotency_key]

            # CASE 2: key exists but is expired - treating it as a new request
            if is_expired(stored["timestamp"]):
                del storage[idempotency_key]

            else :   
                # CASE 3: Same key but DIFFERENT body - rejecting the request
                if stored["body_hash"] != body_hash:
                    raise HTTPException(
                        status_code = 409,
                        detail = "Idempotency key already used for a different request body."
                    )
                
                # CASE 4: Same key, same body - return saved response
                response.headers["X-Cache-Hit"] = "true"
                return stored["response"]
        
        # CASE 5: Key is currently being processed in-flight
        if idempotency_key in in_flight :
            event = in_flight[idempotency_key]
            should_process = False
        else :
            # CASE : Brand new key, creating an event and start processing
            event = threading.Event()
            in_flight[idempotency_key] = event
            should_process = True

    # If another request is already processing this key, wait for it 
    if not should_process :
        event.wait(timeout = 30)

        # Returning the result after waiting
        with lock :
            if idempotency_key in storage :
                stored = storage[idempotency_key]
                response.headers["X-Cache-Hit"] = "true"
                return stored["response"]
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
                "response" : result,
                "timestamp" : datetime.now()
            }
    finally :
        # Always signal waiting requests, even if something goes wrong
        with lock :
            if idempotency_key in in_flight :
                del in_flight[idempotency_key]
        event.set()

    return result
