# setup_installer.py
"""
Script interactivo para crear el archivo .env y preparar el entorno antes de empaquetar el bot como .exe.
Solicita al usuario los datos necesarios y los guarda en .env.
Incluye aceptación del EULA.
"""

import getpass
from pathlib import Path

EULA_FILE = "EULA.txt"
ENV_USER_FILE = ".env.user"

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

def prompt_env_user():
    print("\nPor favor, ingrese los datos personales requeridos para la configuración:")
    telegram_chat_id = input("TELEGRAM_CHAT_ID: ").strip()
    mt5_login = input("MT5_LOGIN (número de cuenta): ").strip()
    mt5_password = getpass.getpass("MT5_PASSWORD: ")
    mt5_server = input("MT5_SERVER: ").strip()
    user_email = input("EMAIL de suscripción: ").strip()
    user_token = input("TOKEN de suscripción: ").strip()

    env_user_content = f"""TELEGRAM_CHAT_ID={telegram_chat_id}
MT5_LOGIN={mt5_login}
MT5_PASSWORD={mt5_password}
MT5_SERVER={mt5_server}
USER_EMAIL={user_email}
USER_TOKEN={user_token}
"""
    with open(ENV_USER_FILE, "w", encoding="utf-8") as f:
        f.write(env_user_content)
    print(f"\nArchivo {ENV_USER_FILE} creado correctamente.")

if __name__ == "__main__":
    print_eula()
    prompt_env_user()
    print("\n¡Configuración inicial completada! Ahora puede empaquetar el bot como .exe.")
