"""
API backend para automatizar y validar suscripciones usando Supabase y Stripe.
Despliega este archivo en Vercel, Render, Railway, etc.
También provee una función validate_subscription(email, token=None) para uso local en el bot.
"""
import os
import requests

# --- API FastAPI para despliegue web (no afecta uso local) ---
try:
    from fastapi import FastAPI, Request, HTTPException
    from fastapi.responses import JSONResponse
    import stripe
    app = FastAPI()
    STRIPE_API_KEY = os.getenv("STRIPE_API_KEY")
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
    if STRIPE_API_KEY:
        stripe.api_key = STRIPE_API_KEY
except ImportError:
    pass


# --- Función utilizable por el bot Python ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")

def validate_subscription(email: str, token: str = None) -> bool:
    """
    Valida la suscripción de un usuario consultando la tabla subscriptions en Supabase.
    Args:
        email: Correo de suscripción
        token: Token de suscripción (obligatorio)
    Returns:
        True si la suscripción está activa, el email y el token coinciden. False en cualquier otro caso.
    """
    if not SUPABASE_URL or not SUPABASE_API_KEY:
        print("[validate_subscription] Variables de entorno SUPABASE_URL o SUPABASE_API_KEY no configuradas.")
        return False
    if token is None or token.strip() == "":
        print("[validate_subscription] Token es obligatorio y no puede estar vacío.")
        return False
    headers = {
        "apikey": SUPABASE_API_KEY,
        "Authorization": f"Bearer {SUPABASE_API_KEY}",
    }
    try:
        # Consultar email y traer active y Token (ojo: mayúscula)
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/subscriptions?email=eq.{email}&select=active,\"Token\"",
            headers=headers,
            timeout=10
        )
        data = resp.json()
        if data and isinstance(data, list) and len(data) > 0:
            record = data[0]
            active = record.get("active")
            db_token = record.get("Token")
            if db_token is None:
                print("[validate_subscription] El usuario existe pero no tiene token registrado en Supabase.")
                return False
            if token != db_token:
                print("[validate_subscription] Token inválido para el usuario.")
                return False
            if active is True:
                return True
            else:
                print("[validate_subscription] Suscripción encontrada pero NO ACTIVA para este usuario.")
                return False
        else:
            print(f"[validate_subscription] Usuario '{email}' no encontrado en Supabase.")
            return False
    except Exception as e:
        print(f"[validate_subscription] Error validando suscripción: {e}")
        return False

# --- Endpoints web para despliegue (no afectan uso local) ---
try:
    @app.post("/webhook/stripe")
    async def stripe_webhook(request: 'Request'):
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

            headers = {
                "apikey": SUPABASE_SERVICE_ROLE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
                "Content-Type": "application/json",
            }
            data = {
                "active": status == "active",
                "expires_at": f"to_timestamp({expires_at})"
            }
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
except Exception:
    pass
