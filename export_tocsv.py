import os
import sqlite3
import pandas as pd
from datetime import datetime
import logging
from dotenv import load_dotenv

load_dotenv()

EXPORT_DIR = os.getenv("EXPORT_DIR", "exports")
DB_PATH = os.getenv("DB_PATH", "trades.db")

os.makedirs(EXPORT_DIR, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(EXPORT_DIR, "export_db.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

def export_sqlite_to_csv(db_path: str, export_dir: str) -> None:
    """
    Exporta todas las tablas de una base de datos SQLite a archivos CSV.
    Los archivos se nombran con timestamp para evitar sobrescritura.
    """
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        if not tables:
            logging.warning("No se encontraron tablas en la base de datos.")
            return

        for table in tables:
            df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{table}_{timestamp}.csv"
            filepath = os.path.join(export_dir, filename)
            df.to_csv(filepath, index=False)
            logging.info(f"Tabla '{table}' exportada a {filepath}")
    except Exception as e:
        logging.error(f"Error exportando la base de datos: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    export_sqlite_to_csv(DB_PATH, EXPORT_DIR)