"""
session.py — In-memory session store keyed by sender_phone.

Sessions are lightweight dicts that track temporary state
between multi-turn conversations (e.g., waiting for name input).

Session structure:
{
    "state":         str,   # e.g. "awaiting_name"
    "updated_at":   float  # epoch seconds (for TTL cleanup)
}

States:
  "idle"          — no pending action
  "awaiting_name" — user triggered BOOK, waiting for them to send their name
"""

import time
import logging
from threading import Lock
from core.config import config

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

STATE_IDLE = "idle"
STATE_AWAITING_NAME = "awaiting_name"

# ── Store ─────────────────────────────────────────────────────────────────────

_store: dict[str, dict] = {}
_lock = Lock()


def _ttl_seconds() -> float:
    return config.SESSION_TIMEOUT_MINUTES * 60


# ── Public API ────────────────────────────────────────────────────────────────

def get_session(phone: str) -> dict:
    """
    Return the session dict for this phone.
    Creates a fresh idle session if none exists or TTL expired.
    """
    with _lock:
        _evict_expired()
        session = _store.get(phone)
        if session is None:
            session = _new_session()
            _store[phone] = session
        return dict(session)  # return a copy


def set_state(phone: str, state: str, **extra) -> None:
    """
    Set the session state for this phone, with optional extra fields.
    Example: set_state(phone, STATE_AWAITING_NAME)
    """
    with _lock:
        session = _store.get(phone, _new_session())
        session["state"] = state
        session["updated_at"] = time.time()
        for key, value in extra.items():
            session[key] = value
        _store[phone] = session
        logger.debug("Session updated: phone=%s state=%s", phone, state)


def clear_session(phone: str) -> None:
    """Reset session to idle and remove extra keys."""
    with _lock:
        _store[phone] = _new_session()
        logger.debug("Session cleared: phone=%s", phone)


def _new_session() -> dict:
    return {"state": STATE_IDLE, "updated_at": time.time()}


def _evict_expired() -> None:
    """Remove sessions older than TTL. Must be called inside _lock."""
    now = time.time()
    ttl = _ttl_seconds()
    expired = [phone for phone, s in _store.items() if (now - s["updated_at"]) > ttl]
    for phone in expired:
        del _store[phone]
        logger.debug("Evicted expired session: phone=%s", phone)
