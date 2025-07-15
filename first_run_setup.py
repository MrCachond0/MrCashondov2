# first_run_setup.py
import os
from cryptography.fernet import Fernet
import getpass

def main():
    print("Bienvenido a Mr. Cashondo Bot - Configuración Inicial\n")
    print("Por favor, introduce los siguientes datos para crear tu archivo .env seguro:")

    # Token y credenciales fijos y cifrados
    telegram_token = "7924378963:AAGH5lHULjkmR5ElychASQjYuM_PGuoe0fA"
    supabase_url = "https://hbbyuxqyatyiazbrezjj.supabase.co"
    supabase_api_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhiYnl1eHF5YXR5aWF6YnJlempqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTIxNzE0MTMsImV4cCI6MjA2Nzc0NzQxM30.fHYeKJGsHvZ83pGcOToJML-3oSlwxNDOXE6fv6pSd4Y"
    print("[INFO] El token de Telegram y las credenciales de Supabase están preconfigurados y no se solicitarán.")
    telegram_chat_id = input("TELEGRAM_CHAT_ID: ").strip()
    mt5_login = input("MT5_LOGIN (número de cuenta): ").strip()
    mt5_password = input("MT5_PASSWORD: ").strip()
    mt5_server = input("MT5_SERVER: ").strip()

    # Genera una clave de cifrado y guárdala en un archivo oculto
    key = Fernet.generate_key()
    with open(".env.key", "wb") as f:
        f.write(key)

    fernet = Fernet(key)
    env_content = f"""TELEGRAM_BOT_TOKEN={telegram_token}\nTELEGRAM_CHAT_ID={telegram_chat_id}\nMT5_LOGIN={mt5_login}\nMT5_PASSWORD={mt5_password}\nMT5_SERVER={mt5_server}\nSUPABASE_URL={supabase_url}\nSUPABASE_API_KEY={supabase_api_key}\n"""
    encrypted = fernet.encrypt(env_content.encode())
    with open(".env.enc", "wb") as f:
        f.write(encrypted)

    print("\n✅ Configuración completada y credenciales cifradas en .env.enc\nEl token de Telegram y Supabase están fijos y seguros.")

if __name__ == "__main__":
    main()