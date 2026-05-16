"""
flows.py — Business logic for all conversation flows.

Each function receives (phone, message) and returns a reply string.
All flows are pure business logic — no HTTP, no Twilio here.

Flows:
  handle_message(phone, message) → str   ← main router, call this
  _flow_main_menu()              → str
  _flow_book_step1(phone)        → str
  _flow_book_step2(phone, name)  → str
  _flow_status(phone)            → str
  _flow_cancel(phone)            → str
  _flow_invalid()                → str
"""

import logging

from core import session, sheets
from core.session import STATE_IDLE, STATE_AWAITING_NAME
from core.config import config

logger = logging.getLogger(__name__)

# ── Keywords ──────────────────────────────────────────────────────────────────

GREET_KEYWORDS  = {"hi", "hello", "start", "hey", "menu"}
BOOK_KEYWORDS   = {"1", "book", "appointment"}
STATUS_KEYWORDS = {"2", "status", "check"}
CANCEL_KEYWORDS = {"3", "cancel"}


# ── Main router ───────────────────────────────────────────────────────────────

def handle_message(phone: str, message: str) -> str:
    """
    Route an incoming message to the correct flow handler.
    Returns the reply string to send back to the patient.
    """
    msg = message.strip().lower()
    sess = session.get_session(phone)
    current_state = sess.get("state", STATE_IDLE)

    logger.info("Handling message: phone=%s state=%s msg=%r", phone, current_state, msg)

    try:
        # - Multi-turn: waiting for patient name
      if current_state == STATE_AWAITING_NAME:
        # Any message in this state is treated as the patient's name
        # UNLESS it looks like a menu command (let them escape)
       if msg in GREET_KEYWORDS:
            session.clear_session(phone)
            return _flow_main_menu()
       if msg in BOOK_KEYWORDS | STATUS_KEYWORDS | CANCEL_KEYWORDS:
            session.clear_session(phone)
            return handle_message(phone, message)
        
        return _flow_book_step2(phone, patient_name=message.strip())  

        # ── Greeting → main menu ─────────────────────────────────────────────
        if msg in GREET_KEYWORDS:
            session.clear_session(phone)
            return _flow_main_menu()

        # ── Book flow step 1 ─────────────────────────────────────────────────
        if msg in BOOK_KEYWORDS:
            return _flow_book_step1(phone)

        # ── Status check ─────────────────────────────────────────────────────
        if msg in STATUS_KEYWORDS:
            return _flow_status(phone)

        # - Cancel -------------------------
        if msg in CANCEL_KEYWORDS:
            return _flow_cancel(phone)

        # - Admin Command ------------------
        if msg == 'next':
            return _flow_next(phone)

        # - Unknown input ------------------
            return _flow_invalid()

    except Exception as exc:
        logger.error("Unhandled error in handle_message: %s", exc, exc_info=True)
        return (
            "⚠️ System temporarily unavailable. Please try again later.\n"
            "If the issue persists, please contact the clinic directly."
        )


# ── Flow: Main Menu ───────────────────────────────────────────────────────────

def _flow_main_menu() -> str:
    return (
        f"👋 Welcome to *{config.CLINIC_NAME}*!\n\n"
        "Please choose an option:\n"
        "1️⃣  *Book Appointment*\n"
        "2️⃣  *Check Queue Status*\n"
        "3️⃣  *Cancel Token*\n\n"
        "_Reply with 1, 2, or 3_"
    )


# ── Flow: Book — Step 1 (ask name) ────────────────────────────────────────────

def _flow_book_step1(phone: str) -> str:
    """
    Begin the booking flow: set session to awaiting_name, ask for name.
    """
    session.set_state(phone, STATE_AWAITING_NAME)
    return (
        "📋 *New Appointment*\n\n"
        "Please reply with your *full name* to proceed.\n\n"
        "_Send 'hi' at any time to return to the main menu._"
    )


# ── Flow: Book — Step 2 (create token) ───────────────────────────────────────

def _flow_book_step2(phone: str, patient_name: str) -> str:
    """
    Finalize the booking after receiving the patient's name.
    Checks for duplicate active tokens, then creates a new one.
    """
    # Guard: empty name
    if not patient_name or len(patient_name.strip()) < 2:
        return (
            "❌ Name seems too short. Please enter your *full name* (at least 2 characters)."
        )

    # Check for existing active token
    existing = sheets.find_active_token(phone)
    if existing:
        session.clear_session(phone)
        return (
            f"⚠️ You already have an active appointment!\n\n"
            f"🎫 *Token #{ existing['token'] }*\n"
            f"Status: {existing['status']}\n\n"
            "Send *2* to check your queue position or *3* to cancel."
        )

    # Generate new token
    new_token = sheets.get_next_token()

    # Write to Google Sheets
    sheets.append_appointment(
        token=new_token,
        name=patient_name.strip(),
        phone=phone,
    )

    # Calculate position
    current_token = sheets.get_current_token()
    all_appts = sheets.get_all_appointments()
    patients_ahead = sum(1 for a in all_appts if a['status'] == 'Waiting' and current_token < a['token'] < new_token)

    # Clear session after successful booking
    session.clear_session(phone)

    return (
        f"✅ *Appointment Confirmed!*\n\n"
        f"👤 Name: {patient_name.strip()}\n"
        f"🎫 Your Token: *#{new_token}*\n"
        f"📍 Current Token: #{current_token}\n"
        f"⏳ Patients ahead of you: *{patients_ahead}*\n\n"
        "Send *2* anytime to check your live queue status.\n"
        "Send *3* to cancel your appointment."
    )


# ── Flow: Check Status ────────────────────────────────────────────────────────

def _flow_status(phone: str) -> str:
    """
    Look up the patient's active token and show their queue position.
    """
    appointment = sheets.find_active_token(phone)

    if not appointment:
        return (
            "❌ *No active appointment found.*\n\n"
            "Send *1* to book a new appointment.\n"
            "Send *hi* to go back to the main menu."
        )

    patient_token = appointment["token"]
    current_token = sheets.get_current_token()
    all_appts     = sheets.get_all_appointments()
    remaining     = sum(1 for a in all_appts if a['status'] == 'Waiting' and current_token < a['token'] < patient_token)

    if remaining <= 0:
        return (
            f"🔔 *It's your turn now!*\n\n"
            f"🎫 Your Token: *#{patient_token}*\n\n"
            f"Please proceed to the reception desk. 🏥"
        )

    return (
        f"📊 *Queue Status*\n\n"
        f"🎫 Your Token: *#{patient_token}*\n"
        f"📍 Current Token: #{current_token}\n"
        f"⏳ Patients ahead of you: *{remaining}*\n\n"
        "_We'll keep serving patients. Thank you for your patience!_"
    )


# ── Flow: Cancel ─────────────────────────────────────────────────────────────

def _flow_cancel(phone: str) -> str:
    """
    Cancel the patient's latest active appointment.
    """
    appointment = sheets.find_active_token(phone)

    if not appointment:
        return (
            "❌ *No active appointment found.*\n\n"
            "Send *1* to book a new appointment.\n"
            "Send *hi* to go back to the main menu."
        )

    sheets.cancel_appointment(appointment["row_index"])

    return (
        f"🚫 *Appointment Cancelled*\n\n"
        f"🎫 Token *#{appointment['token']}* has been cancelled.\n\n"
        "Send *1* to book a new appointment.\n"
        "Send *hi* for the main menu."
    )


# ── Flow: Invalid input ───────────────────────────────────────────────────────

def _flow_invalid() -> str:
    return (
        "❓ *Invalid option.*\n\n"
        "Please reply with:\n"
        "1️⃣  *1* — Book Appointment\n"
        "2️⃣  *2* — Check Queue Status\n"
        "3️⃣  *3* — Cancel Token\n\n"
        "_Or send 'hi' to see the main menu._"
    )

# --- Flow: Admin Next ---

def _flow_next(phone: str) -> str:
    current = sheets.get_current_token()
    new_current = current + 1
    sheets.set_current_token(new_current)
    return (
        f"👨‍⚕️ *Queue Updated!*\n\n"
        f"You are now serving Token: *#{new_current}*\n"
        f"_All patients checking their status will now see the line has moved._"
    )
