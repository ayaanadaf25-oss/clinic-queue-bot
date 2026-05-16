"""
test_flows.py — Unit tests for all conversation flows.

Run with:  python -m pytest core/test_flows.py -v

These tests mock Google Sheets so no real API calls are made.
"""

import pytest
from unittest.mock import patch, MagicMock

# We need to patch sheets before importing flows
import core.session as session_module
from core.session import STATE_IDLE, STATE_AWAITING_NAME


# ── Helpers ───────────────────────────────────────────────────────────────────

PHONE = "+919876543210"

def reset(phone=PHONE):
    session_module.clear_session(phone)


# ── Greeting / Main Menu ──────────────────────────────────────────────────────

class TestMainMenu:
    @pytest.mark.parametrize("msg", ["hi", "hello", "start", "Hey", "HELLO"])
    def test_greetings_show_menu(self, msg):
        reset()
        with patch("core.flows.sheets"):
            from core.flows import handle_message
            reply = handle_message(PHONE, msg)
        assert "Book Appointment" in reply
        assert "Check Queue Status" in reply
        assert "Cancel Token" in reply


# ── Book Flow ─────────────────────────────────────────────────────────────────

class TestBookFlow:
    def test_book_step1_asks_for_name(self):
        reset()
        with patch("core.flows.sheets"):
            from core.flows import handle_message
            reply = handle_message(PHONE, "1")
        assert "full name" in reply.lower()
        assert session_module.get_session(PHONE)["state"] == STATE_AWAITING_NAME

    def test_book_step2_creates_token(self):
        reset()
        mock_sheets = MagicMock()
        mock_sheets.find_active_token.return_value = None
        mock_sheets.get_next_token.return_value = 5
        mock_sheets.get_current_token.return_value = 3

        with patch("core.flows.sheets", mock_sheets):
            from core import flows
            # Step 1
            flows.handle_message(PHONE, "1")
            # Step 2
            reply = flows.handle_message(PHONE, "Rahul Kumar")

        assert "#5" in reply
        assert "Token" in reply
        assert session_module.get_session(PHONE)["state"] == STATE_IDLE
        mock_sheets.append_appointment.assert_called_once_with(
            token=5, name="Rahul Kumar", phone=PHONE
        )

    def test_book_blocks_duplicate_active_token(self):
        reset()
        mock_sheets = MagicMock()
        mock_sheets.find_active_token.return_value = {
            "token": 3, "name": "Rahul", "phone": PHONE,
            "status": "Waiting", "row_index": 4
        }

        with patch("core.flows.sheets", mock_sheets):
            from core import flows
            flows.handle_message(PHONE, "1")   # step 1
            reply = flows.handle_message(PHONE, "Rahul Kumar")  # step 2

        assert "#3" in reply
        assert "already" in reply.lower()
        mock_sheets.append_appointment.assert_not_called()

    def test_book_step2_rejects_empty_name(self):
        reset()
        with patch("core.flows.sheets"):
            from core import flows
            flows.handle_message(PHONE, "1")
            reply = flows.handle_message(PHONE, "A")
        assert "full name" in reply.lower() or "short" in reply.lower()


# ── Status Flow ───────────────────────────────────────────────────────────────

class TestStatusFlow:
    def test_status_no_active_token(self):
        reset()
        mock_sheets = MagicMock()
        mock_sheets.find_active_token.return_value = None

        with patch("core.flows.sheets", mock_sheets):
            from core import flows
            reply = flows.handle_message(PHONE, "2")

        assert "no active" in reply.lower()

    def test_status_shows_position(self):
        reset()
        mock_sheets = MagicMock()
        mock_sheets.find_active_token.return_value = {
            "token": 10, "name": "Rahul", "phone": PHONE,
            "status": "Waiting", "row_index": 11
        }
        mock_sheets.get_current_token.return_value = 7

        with patch("core.flows.sheets", mock_sheets):
            from core import flows
            reply = flows.handle_message(PHONE, "status")

        assert "#10" in reply
        assert "3" in reply  # 3 patients ahead

    def test_status_your_turn(self):
        reset()
        mock_sheets = MagicMock()
        mock_sheets.find_active_token.return_value = {
            "token": 7, "name": "Rahul", "phone": PHONE,
            "status": "Waiting", "row_index": 8
        }
        mock_sheets.get_current_token.return_value = 7

        with patch("core.flows.sheets", mock_sheets):
            from core import flows
            reply = flows.handle_message(PHONE, "2")

        assert "your turn" in reply.lower()


# ── Cancel Flow ───────────────────────────────────────────────────────────────

class TestCancelFlow:
    def test_cancel_no_active_token(self):
        reset()
        mock_sheets = MagicMock()
        mock_sheets.find_active_token.return_value = None

        with patch("core.flows.sheets", mock_sheets):
            from core import flows
            reply = flows.handle_message(PHONE, "3")

        assert "no active" in reply.lower()
        mock_sheets.cancel_appointment.assert_not_called()

    def test_cancel_success(self):
        reset()
        mock_sheets = MagicMock()
        mock_sheets.find_active_token.return_value = {
            "token": 5, "name": "Rahul", "phone": PHONE,
            "status": "Waiting", "row_index": 6
        }

        with patch("core.flows.sheets", mock_sheets):
            from core import flows
            reply = flows.handle_message(PHONE, "cancel")

        assert "cancelled" in reply.lower()
        assert "#5" in reply
        mock_sheets.cancel_appointment.assert_called_once_with(6)


# ── Invalid Input ─────────────────────────────────────────────────────────────

class TestInvalidInput:
    @pytest.mark.parametrize("msg", ["xyz", "4", "???", "book me now"])
    def test_invalid_shows_menu_hint(self, msg):
        reset()
        with patch("core.flows.sheets"):
            from core import flows
            reply = flows.handle_message(PHONE, msg)
        assert "invalid" in reply.lower() or "1" in reply


# ── Session Escape ────────────────────────────────────────────────────────────

class TestSessionEscape:
    def test_can_escape_awaiting_name_with_hi(self):
        reset()
        with patch("core.flows.sheets"):
            from core import flows
            flows.handle_message(PHONE, "1")   # enter booking flow
            assert session_module.get_session(PHONE)["state"] == STATE_AWAITING_NAME
            reply = flows.handle_message(PHONE, "hi")  # escape
        assert "Book Appointment" in reply
        assert session_module.get_session(PHONE)["state"] == STATE_IDLE
