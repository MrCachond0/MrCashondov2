# env_loader.py
import os
from cryptography.fernet import Fernet

def load_env():
    with open(".env.key", "rb") as key_file:
        key = key_file.read()
    fernet = Fernet(key)
    with open(".env.enc", "rb") as enc_file:
        decrypted = fernet.decrypt(enc_file.read()).decode()
    # Cargar variables al entorno
    for line in decrypted.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()