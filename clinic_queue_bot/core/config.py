"""
config.py — Centralized configuration loader
All environment variables are read here. Import `config` anywhere.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Twilio
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_WHATSAPP_NUMBER: str = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

    # Google Sheets
    GOOGLE_SERVICE_ACCOUNT_JSON: str = os.getenv(
        "GOOGLE_SERVICE_ACCOUNT_JSON", "credentials/google_service_account.json"
    )
    SPREADSHEET_NAME: str = os.getenv("SPREADSHEET_NAME", "ClinicQueueBot")
    APPOINTMENTS_SHEET: str = os.getenv("APPOINTMENTS_SHEET", "appointments")
    SETTINGS_SHEET: str = os.getenv("SETTINGS_SHEET", "settings")

    # App
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
    SESSION_TIMEOUT_MINUTES: int = int(os.getenv("SESSION_TIMEOUT_MINUTES", "10"))
    CLINIC_NAME: str = os.getenv("CLINIC_NAME", "ABC Clinic")
    PORT: int = int(os.getenv("PORT", "5000"))

    # Sheet column indices (0-based)
    # appointments: token | name | phone | status | created_at
    COL_TOKEN = 0
    COL_NAME = 1
    COL_PHONE = 2
    COL_STATUS = 3
    COL_CREATED_AT = 4

    # settings: current_token
    COL_CURRENT_TOKEN = 0

    # Status values
    STATUS_WAITING = "Waiting"
    STATUS_CANCELLED = "Cancelled"
    STATUS_DONE = "Done"


config = Config()
