# Turaren Wuta Carnival 2.0 — Ticketing Backend

FastAPI backend: real Paystack payments, capacity enforcement, QR tickets, email confirmation, event-day check-in.

## What this does NOT include yet
- The Supabase transfer channel is enabled through Paystack's own `bank_transfer` channel
  (a dedicated account number per transaction, confirmed automatically via webhook) — **not**
  a manual peer-to-peer bank transfer with WhatsApp screenshots. This removes the need for
  anyone to sit and manually verify payments.
- Nothing here touches the frontend yet. The Bolt/React frontend still needs its `PaystackModal.tsx`
  changed to call this API instead of its current fake `setTimeout`.
- No admin dashboard — for now, check ticket sales directly in the Supabase Table Editor.

## 1. Local setup

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then fill in real values
uvicorn app.main:app --reload
```

Visit `http://localhost:8000/health` — should return `{"status": "ok"}`.
Interactive API docs: `http://localhost:8000/docs`.

## 2. Supabase setup

1. Create a project at supabase.com.
2. Project Settings → Database → Connection string → copy the **Session pooler** URI into `DATABASE_URL` in `.env`.
3. Either run `supabase_schema.sql` in the SQL Editor, or just start the app once — it auto-creates the `tickets` table.

## 3. Paystack setup

1. Complete business KYC verification (do this first — it has the longest lead time).
2. Dashboard → Settings → API Keys & Webhooks → copy your **test** secret/public keys into `.env` first.
3. In the same page, set your **Webhook URL** to: `https://your-backend-domain.com/webhook/paystack`
   (Paystack can't reach `localhost` — use [ngrok](https://ngrok.com) to test webhooks locally before you deploy.)
4. Only switch to live (`sk_live_...`) keys after a full successful test run.

## 4. Email (Resend)

1. Sign up at resend.com, verify a sending domain (or use their test domain while developing).
2. Copy the API key into `RESEND_API_KEY`.

## 5. Deploying to Render

- New Web Service → connect this repo.
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Add all the `.env` values as environment variables in Render's dashboard (never commit `.env`).
- **Use a paid instance, not the free tier** — free tier sleeps after inactivity, and your first
  buyer of the day would hit a 10–20 second hang before the API wakes up.

## 6. How the frontend should call this

```js
// On "Buy Ticket" submit, instead of the current fake setTimeout:
const res = await fetch(`${API_URL}/checkout/init`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ name, email, phone, payment_method: 'card' }), // or 'bank_transfer'
});
const { authorization_url } = await res.json();
window.location.href = authorization_url; // sends the buyer to Paystack's hosted checkout
```

Paystack redirects back to `FRONTEND_SUCCESS_URL` after payment. Build that page to poll
`GET /tickets/capacity` or just show "check your email for your ticket" — the webhook, not
the redirect, is what actually confirms payment and sends the QR code, so there can be a
few seconds' lag between the redirect landing and the email arriving.

## 7. Check-in on event day

`POST /checkin` with `{ "ticket_ref": "...", "token": "..." }` (both are encoded in the QR code
your scanner reads). Build a one-page scanner UI later — the endpoint itself is ready now.
