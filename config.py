# config.py
import os
import secrets
from dotenv import load_dotenv

load_dotenv() 

class Config:
    # --- Secret Key Handling ---
    SECRET_FILE = "/opt/ngs_webinterface/.secret_key"

    if os.getenv("SECRET_KEY"):
        SECRET_KEY = os.getenv("SECRET_KEY")
    else:
        # Wenn Datei existiert → laden
        if os.path.exists(SECRET_FILE):
            with open(SECRET_FILE, "r") as f:
                SECRET_KEY = f.read().strip()
        else:
            # Neuen Schlüssel erzeugen und speichern
            SECRET_KEY = secrets.token_hex(32)
            os.makedirs(os.path.dirname(SECRET_FILE), exist_ok=True)
            with open(SECRET_FILE, "w") as f:
                f.write(SECRET_KEY)
            print(f"[INFO] Neuer SECRET_KEY erzeugt und in {SECRET_FILE} gespeichert")

    # --- Database Configuration ---
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
