"""
whatsapp.py — Twilio WhatsApp sender utility.

Provides send_whatsapp_reply(to, body) used by the webhook handler.
Also provides build_twiml_reply(body) for TwiML-based responses
(simpler, no outbound API call needed — Twilio handles delivery automatically).
"""

import logging
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client as TwilioClient

from core.config import config

logger = logging.getLogger(__name__)

_twilio_client = None


def _get_twilio_client() -> TwilioClient:
    global _twilio_client
    if _twilio_client is None:
        _twilio_client = TwilioClient(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
    return _twilio_client


def build_twiml_reply(body: str) -> str:
    """
    Build a TwiML XML string for replying in the same webhook response.
    This is the RECOMMENDED approach — no extra API call needed.
    Twilio reads this XML from your webhook response and sends the WhatsApp message.

    Usage: return this string from your Flask route with mimetype='text/xml'
    """
    resp = MessagingResponse()
    resp.message(body)
    return str(resp)


def send_whatsapp_reply(to: str, body: str) -> None:
    """
    Send a WhatsApp message via Twilio REST API (outbound).
    Use this when you need to send a message OUTSIDE a webhook context
    (e.g., a scheduled reminder, async notification).

    Args:
        to:   recipient, e.g. 'whatsapp:+919876543210'
        body: message text
    """
    try:
        client = _get_twilio_client()
        message = client.messages.create(
            from_=config.TWILIO_WHATSAPP_NUMBER,
            to=to,
            body=body,
        )
        logger.info("WhatsApp message sent: sid=%s to=%s", message.sid, to)
    except Exception as exc:
        logger.error("send_whatsapp_reply failed: to=%s error=%s", to, exc)
        raise
