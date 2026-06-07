"""
app.py — Clinic Queue WhatsApp Bot
===================================
Flask webhook server entry point.

Incoming POST /webhook  ← Twilio sends WhatsApp messages here
GET  /health            ← health check endpoint
GET  /queue             ← internal dashboard: view live queue (no auth, add one in prod)

Twilio setup:
  In Twilio Console → WhatsApp Sandbox (or your number) → 
  Webhook URL: https://your-domain.com/webhook
  Method: HTTP POST
"""

import logging
import sys
from flask import Flask, request, Response, jsonify

from core.config import config
from core.flows import handle_message
from core.whatsapp import build_twiml_reply
from core import sheets

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ── Flask app ─────────────────────────────────────────────────────────────────

app = Flask(__name__)
app.secret_key = config.SECRET_KEY


# ── Webhook: receive WhatsApp messages ───────────────────────────────────────

@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Twilio posts here when a patient sends a WhatsApp message.

    Expected form fields (Twilio standard):
      Body   — message text
      From   — sender number, e.g. 'whatsapp:+919876543210'
      To     — your Twilio number

    Returns TwiML XML which Twilio converts into a WhatsApp reply.
    """
    try:
        message_body = request.form.get("Body", "").strip()
        sender_raw   = request.form.get("From", "").strip()

        # Normalise phone: strip 'whatsapp:' prefix for internal use
        sender_phone = sender_raw.replace("whatsapp:", "").strip()

        if not message_body or not sender_phone:
            logger.warning("Received empty message or sender. Ignoring.")
            return Response(build_twiml_reply(""), mimetype="text/xml")

        logger.info("Incoming WhatsApp | from=%s | msg=%r", sender_phone, message_body)

        # Core business logic
        reply = handle_message(phone=sender_phone, message=message_body)

        logger.info("Reply to %s: %r", sender_phone, reply[:80])

        return Response(build_twiml_reply(reply), mimetype="text/xml")

    except Exception as exc:
        logger.error("Webhook error: %s", exc, exc_info=True)
        fallback = (
            "⚠️ System temporarily unavailable. Please try again in a moment."
        )
        return Response(build_twiml_reply(fallback), mimetype="text/xml")


# ── Health check ─────────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    """Simple health check — returns 200 OK with status info."""
    return jsonify({
        "status": "ok",
        "clinic": config.CLINIC_NAME,
        "spreadsheet": config.SPREADSHEET_NAME,
    })


# ── Internal queue dashboard ──────────────────────────────────────────────────

@app.route("/queue", methods=["GET"])
def queue_dashboard():
    """
    Internal endpoint: view live queue state.
    Returns JSON with current token and all waiting appointments.

    ⚠️  Add authentication before exposing this in production.
    """
    try:
        current_token = sheets.get_current_token()
        appointments  = sheets.get_all_appointments()
        waiting = [a for a in appointments if a["status"] == "Waiting"]
        done    = [a for a in appointments if a["status"] == "Done"]
        cancelled = [a for a in appointments if a["status"] == "Cancelled"]

        return jsonify({
            "current_token": current_token,
            "waiting_count": len(waiting),
            "waiting":       waiting,
            "done_count":    len(done),
            "cancelled_count": len(cancelled),
        })
    except Exception as exc:
        logger.error("Queue dashboard error: %s", exc)
        return jsonify({"error": str(exc)}), 500
@app.route('/tracker', methods=['GET'])
def live_tracker():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Patient Queue Tracker</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-50 min-h-screen flex flex-col items-center justify-center p-4 font-sans">
        
        <div class="text-center mb-8">
            <h1 class="text-2xl font-bold text-slate-800">Patient Queue Tracker</h1>
            <p class="text-slate-500 text-sm mt-1">Real-time clinic status</p>
        </div>

        <!-- Now Serving Card -->
        <div class="w-full max-w-md bg-white rounded-2xl shadow-sm border border-slate-100 p-8 text-center mb-6">
            <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-4">Now Serving</p>
            <div class="text-8xl font-bold text-blue-600 tracking-tighter" id="current-token">--</div>
            <div class="h-1 w-16 bg-blue-500 mx-auto mt-6 rounded-full"></div>
        </div>

        <!-- Details Grid -->
        <div class="w-full max-w-md grid grid-cols-2 gap-4">
            <div class="bg-white rounded-2xl shadow-sm border border-slate-100 p-6 text-center">
                <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-2">Total Waiting</p>
                <div class="text-4xl font-bold text-slate-800" id="total-waiting">--</div>
                <p class="text-xs text-slate-400 mt-2">patients</p>
            </div>
            
            <div class="bg-white rounded-2xl shadow-sm border border-slate-100 p-6 text-center">
                <p class="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-2">Est. Wait</p>
                <div class="text-4xl font-bold text-slate-800" id="est-wait">--</div>
                <p class="text-xs text-slate-400 mt-2">minutes</p>
            </div>
        </div>

        <div class="mt-8 flex items-center justify-center gap-2 text-xs text-slate-400">
            <span class="relative flex h-2 w-2">
              <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
              <span class="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
            </span>
            Live updating every 5 seconds
        </div>

        <script>
            function fetchQueue() {
                // Pointing to your exact /queue endpoint
                fetch('/queue')
                    .then(res => res.json())
                    .then(data => {
                        // Using your exact waiting_count variable
                        if(data.current_token !== undefined) {
                            document.getElementById('current-token').innerText = '#' + data.current_token;
                            document.getElementById('total-waiting').innerText = data.waiting_count;
                            document.getElementById('est-wait').innerText = '~' + (data.waiting_count * 10);
                        }
                    })
                    .catch(err => console.error("Error fetching queue:", err));
            }
            fetchQueue();
            setInterval(fetchQueue, 5000);
        </script>
    </body>
    </html>
    """
    return html_content

# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logger.info("Starting %s on port %s", config.CLINIC_NAME, config.PORT)
    app.run(host="0.0.0.0", port=config.PORT, debug=False)
