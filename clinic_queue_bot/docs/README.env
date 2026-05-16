# Clinic Queue WhatsApp Bot 🏥

A production-ready WhatsApp queue management system for clinics.  
Patients can **book**, **check status**, and **cancel** appointments via WhatsApp.  
The receptionist only needs to update one cell in Google Sheets to advance the queue.

---

## Architecture

```
WhatsApp Patient
      │ sends message
      ▼
Twilio WhatsApp API
      │ HTTP POST
      ▼
Flask Webhook (/webhook)          ← app.py
      │
      ├─ flows.py   (routing + business logic)
      │       │
      │       ├─ session.py   (in-memory per-phone state)
      │       └─ sheets.py    (Google Sheets read/write)
      │
      └─ whatsapp.py  (build TwiML reply)
             │
             ▼
      Twilio → Patient's WhatsApp
```

---

## Project Structure

```
clinic_queue_bot/
├── app.py                  ← Flask server + webhook endpoint
├── requirements.txt
├── .env.example            ← copy to .env and fill in
├── core/
│   ├── config.py           ← all environment variables
│   ├── sheets.py           ← Google Sheets database layer
│   ├── session.py          ← in-memory session state
│   ├── flows.py            ← business logic (booking, status, cancel)
│   ├── whatsapp.py         ← Twilio TwiML helper
│   └── test_flows.py       ← unit tests (pytest)
├── credentials/
│   └── google_service_account.json  ← (you add this, not committed)
└── docs/
    └── README.md
```

---

## Setup Guide

### Step 1 — Clone & install dependencies

```bash
git clone <your-repo>
cd clinic_queue_bot
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

### Step 2 — Google Sheets setup

#### 2a. Create the spreadsheet

1. Go to [sheets.google.com](https://sheets.google.com) → create new spreadsheet
2. Name it exactly: **`ClinicQueueBot`**

#### 2b. Create Sheet 1 — `appointments`

| token | name | phone | status | created_at |
|-------|------|-------|--------|------------|
| (header row only, leave data rows empty) |

#### 2c. Create Sheet 2 — `settings`

| current_token |
|---------------|
| 0             |

> **Receptionist workflow**: When serving the next patient, change the `current_token` cell value from 0 → 1 → 2 etc. That's all they need to do!

#### 2d. Create a Google Service Account

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (or use existing)
3. Enable APIs: **Google Sheets API** + **Google Drive API**
4. Go to **IAM & Admin → Service Accounts → Create**
5. Give it any name (e.g. `clinic-bot`)
6. Create a JSON key → download it
7. Save it as: `credentials/google_service_account.json`
8. **Share your spreadsheet** with the service account's email address (Editor access)

---

### Step 3 — Twilio WhatsApp setup

1. Sign up at [twilio.com](https://twilio.com)
2. Go to **Messaging → Try it out → Send a WhatsApp Message**
3. Note your **Sandbox number** (e.g. `+14155238886`)
4. Note your **Account SID** and **Auth Token** from the dashboard
5. Set the sandbox webhook URL (after deploying) → see Step 5

---

### Step 4 — Environment configuration

```bash
cp .env.example .env
```

Edit `.env`:

```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

GOOGLE_SERVICE_ACCOUNT_JSON=credentials/google_service_account.json
SPREADSHEET_NAME=ClinicQueueBot
APPOINTMENTS_SHEET=appointments
SETTINGS_SHEET=settings

SECRET_KEY=some-long-random-string
CLINIC_NAME=ABC Clinic
SESSION_TIMEOUT_MINUTES=10
PORT=5000
```

---

### Step 5 — Run locally (with ngrok for testing)

```bash
# Terminal 1 — run the Flask app
python app.py

# Terminal 2 — expose it via ngrok
ngrok http 5000
```

Copy the ngrok HTTPS URL (e.g. `https://abc123.ngrok.io`).

In Twilio Console → **WhatsApp Sandbox Settings**:
- **When a message comes in**: `https://abc123.ngrok.io/webhook`
- Method: `HTTP POST`

---

### Step 6 — Run tests

```bash
cd clinic_queue_bot
python -m pytest core/test_flows.py -v
```

Expected output: all tests pass ✅

---

### Step 7 — Deploy to production

**Option A: Railway.app (recommended, free tier)**
```bash
# Install Railway CLI
npm install -g @railway/cli
railway login
railway init
railway up
```

**Option B: Render.com**
- Connect your GitHub repo
- Set Start Command: `gunicorn app:app --workers 2 --bind 0.0.0.0:$PORT`
- Add all `.env` variables in the Render dashboard

**Option C: VPS / EC2**
```bash
gunicorn app:app --workers 2 --bind 0.0.0.0:5000 --daemon
```

After deploying, update your Twilio webhook URL from ngrok to your production URL.

---

## Conversation Flow

```
Patient sends: "hi" / "hello" / "start"
───────────────────────────────────────
Bot: Welcome to ABC Clinic!
     1. Book Appointment
     2. Check Queue Status  
     3. Cancel Token

─────────────────────────────────────────────────
FLOW 1: Book (send "1" or "book")
─────────────────────────────────────────────────
Bot: Please reply with your full name.
Patient: Rahul Kumar
Bot: ✅ Appointment Confirmed!
     🎫 Your Token: #19
     📍 Current Token: #12
     ⏳ Patients ahead of you: 6

─────────────────────────────────────────────────
FLOW 2: Check Status (send "2" or "status")
─────────────────────────────────────────────────
Bot: 📊 Queue Status
     🎫 Your Token: #19
     📍 Current Token: #15
     ⏳ Patients ahead of you: 3

─────────────────────────────────────────────────
FLOW 3: Cancel (send "3" or "cancel")
─────────────────────────────────────────────────
Bot: 🚫 Appointment Cancelled
     Token #19 has been cancelled.
```

---

## Receptionist Guide

The receptionist only needs to manage **one cell** in Google Sheets:

| Sheet | Cell | Action |
|-------|------|--------|
| `settings` | A2 | Update the number to the **current token being served** |

Example: When calling token #13, change the value from `12` to `13`.

Patients checking their status will automatically see the updated queue position.

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/webhook` | POST | Twilio WhatsApp webhook (main entry point) |
| `/health` | GET | Health check — returns `{"status": "ok"}` |
| `/queue` | GET | Live queue dashboard (JSON) — add auth before production use |

---

## Customization

| What to change | Where |
|----------------|-------|
| Clinic name | `CLINIC_NAME` in `.env` |
| Session timeout | `SESSION_TIMEOUT_MINUTES` in `.env` |
| Add new keywords | `BOOK_KEYWORDS`, `STATUS_KEYWORDS`, etc. in `flows.py` |
| Change reply messages | Message strings in `flows.py` |
| Add appointment time slots | Extend `append_appointment()` in `sheets.py` |
| Add SMS fallback | Use `send_whatsapp_reply()` in `whatsapp.py` |
| Switch to Redis sessions | Replace `_store` dict in `session.py` with Redis client |

---

## Production Checklist

- [ ] `.env` filled with real credentials (never commit this file)
- [ ] `credentials/google_service_account.json` added (never commit)
- [ ] `.gitignore` includes `.env` and `credentials/`
- [ ] Twilio webhook URL updated to production URL
- [ ] Google Sheet shared with service account email
- [ ] `/queue` endpoint protected with authentication
- [ ] Gunicorn used instead of `flask run`
- [ ] HTTPS enforced (Twilio requires it)
- [ ] Consider Redis for sessions if running multiple workers

---

## Support

For issues: check `app.py` logs — all flows log at INFO level with phone number and message.
