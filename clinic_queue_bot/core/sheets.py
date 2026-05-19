"""
sheets.py — Google Sheets database layer
All read/write/update operations for ClinicQueueBot spreadsheet.

Sheet: appointments
  Columns: token | name | phone | status | created_at

Sheet: settings
  Columns: current_token  (single row, row index 2)
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials

from core.config import config

logger = logging.getLogger(__name__)

# Google API scopes required
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ── Singleton client ──────────────────────────────────────────────────────────

_gc: Optional[gspread.Client] = None


def _get_client() -> gspread.Client:
    """Return a cached gspread client; create it if not yet initialized."""
    global _gc
    if _gc is None:
        creds = Credentials.from_service_account_file(
            config.GOOGLE_SERVICE_ACCOUNT_JSON, scopes=SCOPES
        )
        _gc = gspread.authorize(creds)
        logger.info("Google Sheets client initialized.")
    return _gc


def _get_sheet(sheet_name: str) -> gspread.Worksheet:
    client = _get_client()
    spreadsheet = client.open("ClinicQueueBot")
    return spreadsheet.worksheet(sheet_name)

# ── appointments sheet ────────────────────────────────────────────────────────

def get_all_appointments() -> list[dict]:
    """
    Return all appointment rows (excluding header) as list of dicts:
    {row_index, token, name, phone, status, created_at}
    row_index is 1-based (actual Google Sheets row number).
    """
    try:
        ws = _get_sheet(config.APPOINTMENTS_SHEET)
        rows = ws.get_all_values()  # includes header at index 0
        appointments = []
        for i, row in enumerate(rows[1:], start=2):  # row 2 onward in sheet
            if not any(row):  # skip empty rows
                continue
            appointments.append({
                "row_index": i,
                "token":      int(row[config.COL_TOKEN]) if row[config.COL_TOKEN].isdigit() else 0,
                "name":       row[config.COL_NAME],
                "phone": "+" + str(row[config.COL_PHONE]).replace("+", ""),
                "status":     row[config.COL_STATUS],
                "created_at": row[config.COL_CREATED_AT],
            })
        return appointments
    except Exception as exc:
        logger.error("get_all_appointments failed: %s", exc)
        raise


def find_active_token(phone: str) -> Optional[dict]:
    """
    Return the latest Waiting appointment for this phone number, or None.
    """
    try:
        appointments = get_all_appointments()
        matches = [
            a for a in appointments
            if a["phone"] == phone and a["status"] == config.STATUS_WAITING
        ]
        if not matches:
            return None
        # Return the one with the highest token (latest booking)
        return max(matches, key=lambda a: a["token"])
    except Exception as exc:
        logger.error("find_active_token failed: %s", exc)
        raise


def get_next_token() -> int:
    """
    Read all rows and return max(token) + 1.
    If no rows exist yet, start at 1.
    """
    try:
        appointments = get_all_appointments()
        if not appointments:
            return 1
        return max(a["token"] for a in appointments) + 1
    except Exception as exc:
        logger.error("get_next_token failed: %s", exc)
        raise


def append_appointment(token: int, name: str, phone: str) -> None:
    """
    Append a new row to the appointments sheet.
    """
    try:
        ws = _get_sheet(config.APPOINTMENTS_SHEET)
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        ws.append_row(
            [token, name, phone, config.STATUS_WAITING, now_iso],
            value_input_option="USER_ENTERED",
        )
        logger.info("Appended appointment: token=%s phone=%s", token, phone)
    except Exception as exc:
        logger.error("append_appointment failed: %s", exc)
        raise


def cancel_appointment(row_index: int) -> None:
    """
    Update the status cell of a specific row to 'Cancelled'.
    row_index is 1-based (actual Google Sheets row number).
    """
    try:
        ws = _get_sheet(config.APPOINTMENTS_SHEET)
        # status column is COL_STATUS (0-based) → convert to 1-based for gspread
        status_col = config.COL_STATUS + 1
        ws.update_cell(row_index, status_col, config.STATUS_CANCELLED)
        logger.info("Cancelled appointment at row %s", row_index)
    except Exception as exc:
        logger.error("cancel_appointment failed: %s", exc)
        raise


# ── settings sheet ────────────────────────────────────────────────────────────

def get_current_token() -> int:
    """
    Read the current_token value from the settings sheet (row 2, col A).
    Returns 0 if not set.
    """
    try:
        ws = _get_sheet(config.SETTINGS_SHEET)
        value = ws.cell(2, 1).value  # row 2, column 1 (header is row 1)
        if value and str(value).strip().isdigit():
            return int(str(value).strip())
        return 0
    except Exception as exc:
        logger.error("get_current_token failed: %s", exc)
        raise

def set_current_token(new_token: int) -> None:
    """Admin function to update the current token in settings."""
    try:
        ws = _get_sheet(config.SETTINGS_SHEET)
        ws.update_cell(2, 1, new_token) # Row 2, Col A
        logger.info("Admin updated current token to %s", new_token)
    except Exception as exc:
        logger.error("set_current_token failed: %s", exc)
        raise

def get_patient_by_token(target_token: int) -> dict:
    """
    Searches the sheet for a specific waiting token and returns their data.
    """
    appointments = get_all_appointments()
    
    for appt in appointments:
        # Check if the token matches AND they are still waiting
        if appt.get('token') == target_token and appt.get('status') == 'Waiting':
            return appt
            
    return None
