# setup_installer.py
"""
Script interactivo para crear el archivo .env y preparar el entorno antes de empaquetar el bot como .exe.
Solicita al usuario los datos necesarios y los guarda en .env.
Incluye aceptación del EULA.
"""
import os
from pathlib import Path
from getpass import getpass

EULA_FILE = "EULA.txt"
ENV_FILE = ".env"


def print_eula():
    """Muestra el EULA y solicita aceptación."""
    if not Path(EULA_FILE).exists():
        print("No se encontró el archivo EULA.txt. Abortando.")
        exit(1)
    with open(EULA_FILE, encoding="utf-8") as f:
        print(f.read())
    resp = input("\n¿Acepta los términos del EULA? (s/n): ").strip().lower()
    if resp != "s":
        print("Debe aceptar el EULA para continuar.")
        exit(1)

def prompt_env():
    """Solicita los datos al usuario y los guarda en .env."""
    print("\nPor favor, ingrese los datos requeridos para la configuración:")
    mt5_login = input("MT5 Login: ").strip()
    mt5_password = getpass("MT5 Password: ")
    mt5_server = input("MT5 Server: ").strip()
    telegram_token = getpass("Telegram Bot Token: ")
    telegram_chat_id = input("Telegram Chat ID: ").strip()
    supabase_url = input("Supabase URL (opcional): ").strip()
    supabase_key = getpass("Supabase API Key (opcional): ")

    env_lines = [
        f"MT5_LOGIN={mt5_login}",
        f"MT5_PASSWORD={mt5_password}",
        f"MT5_SERVER={mt5_server}",
        f"TELEGRAM_TOKEN={telegram_token}",
        f"TELEGRAM_CHAT_ID={telegram_chat_id}",
    ]
    if supabase_url:
        env_lines.append(f"SUPABASE_URL={supabase_url}")
    if supabase_key:
        env_lines.append(f"SUPABASE_KEY={supabase_key}")

    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(env_lines) + "\n")
    print(f"\nArchivo {ENV_FILE} creado correctamente.")

if __name__ == "__main__":
    print_eula()
    prompt_env()
    print("\n¡Configuración inicial completada! Ahora puede empaquetar el bot como .exe.")
