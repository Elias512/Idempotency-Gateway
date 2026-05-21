from fastapi import FastAPI, Header, HTTPException, Response
from pydantic import BaseModel
import time
import hashlib
import json

# Creating the FastAPI application
app = FastAPI()

# The notebook to store all processed payments
storage = {}

# Defining how the payment request should look like
class PaymentRequest(BaseModel):
    amount: float
    currency: str

def hash_body(payment: PaymentRequest):
    # Converting the payment body into a unique fingerprint
    body_str = json.dumps(payment.dict(), sort_keys=True)
    return hashlib.md5(body_str.encode()).hexdigest()

@app.post("/process_payment")
def process_payment(
    payment: PaymentRequest,
    idempotency_key: str = Header(...),
    response: Response = None
):
    body_hash = hash_body(payment)

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


    # CASE 4: Brand new key - Simulating payment processing delay (2 seconds)
    time.sleep(2)

    result = {
        "status" : "success",
        "message" : f"Charged {payment.amount} {payment.currency}"
    }

    # Storing the result in the notebook with the key and body hash
    storage[idempotency_key] = {
        "body_hash": body_hash,
        "response": result
    }

    return result
