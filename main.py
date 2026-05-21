from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import time

# Creating the FastAPI application
app = FastAPI()

# Defining how the payment request should look like
class PaymentRequest(BaseModel):
    amount: float
    currency: str


@app.post("/process_payment")
def process_payment(
    payment: PaymentRequest,
    idempotency_key: str = Header(...)
):
    # Simulating payment processing delay (2 seconds)
    time.sleep(2)

    # Returning a success response with the payment details
    return {
        "status" : "success",
        "message" : f"Charged {payment.amount} {payment.currency}"
    }
