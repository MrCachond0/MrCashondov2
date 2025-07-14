# env_loader.py
import os
from cryptography.fernet import Fernet

def load_env():
    try:
        if not os.path.exists(".env.key") or not os.path.exists(".env.enc"):
            print("\n[CONFIG] No se encontraron archivos de entorno cifrados (.env.key y/o .env.enc).\nSe lanzará el asistente de configuración inicial.\n")
            import subprocess
            import sys
            # Ejecutar el asistente de configuración
            result = subprocess.run([sys.executable, "first_run_setup.py"])
            if result.returncode != 0:
                print("[CONFIG] El asistente de configuración no se completó correctamente. Por favor, ejecuta 'first_run_setup.py' manualmente.")
                sys.exit(1)
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
    except Exception as e:
        print(f"[ERROR][ENV] No se pudieron cargar las variables de entorno: {e}")
        print("Por favor, ejecuta 'first_run_setup.py' para configurar tus credenciales.")
        import sys
        sys.exit(1)