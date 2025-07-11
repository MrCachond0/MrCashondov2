# first_run_setup.py
import os
from cryptography.fernet import Fernet
import getpass

def main():
    print("Bienvenido a Mr. Cashondo Bot - Configuración Inicial\n")
    print("Por favor, introduce los siguientes datos para crear tu archivo .env seguro:")

    telegram_token = input("TELEGRAM_BOT_TOKEN: ").strip()
    telegram_chat_id = input("TELEGRAM_CHAT_ID: ").strip()
    mt5_login = input("MT5_LOGIN (número de cuenta): ").strip()
    mt5_password = input("MT5_PASSWORD: ").strip()
    mt5_server = input("MT5_SERVER: ").strip()

    # Genera una clave de cifrado y guárdala en un archivo oculto
    key = Fernet.generate_key()
    with open(".env.key", "wb") as f:
        f.write(key)

    fernet = Fernet(key)
    env_content = f"""TELEGRAM_BOT_TOKEN={telegram_token}
TELEGRAM_CHAT_ID={telegram_chat_id}
MT5_LOGIN={mt5_login}
MT5_PASSWORD={mt5_password}
MT5_SERVER={mt5_server}
"""
    encrypted = fernet.encrypt(env_content.encode())
    with open(".env.enc", "wb") as f:
        f.write(encrypted)

    print("\n✅ Configuración completada y credenciales cifradas en .env.enc")

if __name__ == "__main__":
    main()