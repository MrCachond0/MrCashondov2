"""
API backend para automatizar y validar suscripciones usando Supabase y Stripe.
Despliega este archivo en Vercel, Render, Railway, etc.
"""
import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import stripe
import requests

app = FastAPI()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

stripe.api_key = STRIPE_API_KEY

@app.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if event["type"] == "customer.subscription.updated":
        subscription = event["data"]["object"]
        customer_id = subscription["customer"]
        status = subscription["status"]
        expires_at = subscription["current_period_end"]

        # Busca el usuario en Supabase por stripe_customer_id
        headers = {
            "apikey": SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/json",
        }
        # Actualiza el estado de la suscripción
        data = {
            "active": status == "active",
            "expires_at": f"to_timestamp({expires_at})"
        }
        # PATCH en Supabase
        requests.patch(
            f"{SUPABASE_URL}/rest/v1/subscriptions?stripe_customer_id=eq.{customer_id}",
            headers=headers,
            json=data,
        )
    return JSONResponse({"status": "ok"})

@app.get("/validate")
async def validate(email: str):
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    }
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/subscriptions?email=eq.{email}&select=active,expires_at",
        headers=headers,
    )
    data = resp.json()
    if data and data[0]["active"]:
        return {"valid": True, "expires_at": data[0]["expires_at"]}
    return {"valid": False}
