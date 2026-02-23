# Onboarding Guide

This guide walks you through configuring the Airbnb/VRBO Hosting Automation platform after your first boot. By the end, you'll have task scheduling, properties, notifications, and payment tracking fully configured.

**Prerequisites:** The platform is running via `docker-compose up` (or equivalent), and you can access the dashboard at `http://localhost:3000` and the API at `http://localhost:8000`.

---

## Table of Contents

1. [Celery Beat Configuration (Task Scheduling)](#1-celery-beat-configuration-task-scheduling)
2. [Adding Properties](#2-adding-properties)
3. [Notification Setup (SendGrid + Twilio)](#3-notification-setup-sendgrid--twilio)
4. [Stripe Payment Tracking](#4-stripe-payment-tracking)

---

## 1. Celery Beat Configuration (Task Scheduling)

Celery Beat is the scheduler that drives all automation. It runs periodic tasks that poll for bookings, generate tasks, check statuses, and send notifications.

### Understanding the Tasks

| Task | Default Schedule | What It Does |
|------|-----------------|--------------|
| `poll_airbnb_bookings` | Every 15 min (`*/15`) | Syncs new Airbnb bookings across all properties |
| `poll_vrbo_bookings` | Every 15 min (offset: `7,22,37,52`) | Syncs new VRBO bookings (staggered to avoid API overlap) |
| `auto_book_pending_tasks` | Every 30 min (`*/30`) | Books humans via RentAHuman for pending cleaning/maintenance tasks |
| `check_booking_statuses` | Every hour (`:00`) | Polls RentAHuman for status updates on active bookings |
| `send_daily_summary` | Daily at 8:00 AM | Sends email summary of today's tasks, upcoming work, and issues |

Task generation (`generate_tasks_for_booking`) is **event-driven**, not scheduled — it triggers automatically when a new booking is detected by polling.

### How to Customize the Schedule

The beat schedule is defined in `backend/celery_config.py` under `beat_schedule`. To customize it, edit that file directly.

#### Example: High-Volume Daily Rental (Frequent Turnovers)

Poll more frequently and book humans faster:

```python
beat_schedule={
    "poll-airbnb-bookings": {
        "task": "tasks.polling.poll_airbnb_bookings",
        "schedule": crontab(minute="*/5"),           # Every 5 minutes
        "options": {"queue": "polling"},
    },
    "poll-vrbo-bookings": {
        "task": "tasks.polling.poll_vrbo_bookings",
        "schedule": crontab(minute="2,7,12,17,22,27,32,37,42,47,52,57"),
        "options": {"queue": "polling"},
    },
    "auto-book-pending-tasks": {
        "task": "tasks.booking_automation.auto_book_pending_tasks",
        "schedule": crontab(minute="*/10"),          # Every 10 minutes
        "options": {"queue": "booking"},
    },
    "check-booking-statuses": {
        "task": "tasks.status_check.check_booking_statuses",
        "schedule": crontab(minute="*/30"),           # Every 30 minutes
        "options": {"queue": "default"},
    },
    "daily-summary-report": {
        "task": "tasks.notifications.send_daily_summary",
        "schedule": crontab(hour="7", minute="0"),   # 7 AM
        "options": {"queue": "notifications"},
    },
}
```

#### Example: Weekly Vacation Rental (Lower Volume)

Poll less frequently to reduce API usage:

```python
beat_schedule={
    "poll-airbnb-bookings": {
        "task": "tasks.polling.poll_airbnb_bookings",
        "schedule": crontab(minute="0"),              # Every hour
        "options": {"queue": "polling"},
    },
    "poll-vrbo-bookings": {
        "task": "tasks.polling.poll_vrbo_bookings",
        "schedule": crontab(minute="30"),             # Every hour (offset)
        "options": {"queue": "polling"},
    },
    "auto-book-pending-tasks": {
        "task": "tasks.booking_automation.auto_book_pending_tasks",
        "schedule": crontab(minute="0", hour="*/2"),  # Every 2 hours
        "options": {"queue": "booking"},
    },
    "check-booking-statuses": {
        "task": "tasks.status_check.check_booking_statuses",
        "schedule": crontab(minute="0", hour="*/4"),  # Every 4 hours
        "options": {"queue": "default"},
    },
    "daily-summary-report": {
        "task": "tasks.notifications.send_daily_summary",
        "schedule": crontab(hour="9", minute="0"),    # 9 AM
        "options": {"queue": "notifications"},
    },
}
```

### Task Queues

Tasks are routed to separate queues for isolation:

| Queue | Tasks |
|-------|-------|
| `polling` | Booking sync from Airbnb/VRBO |
| `booking` | RentAHuman auto-booking |
| `notifications` | Email/SMS sending |
| `default` | Task generation, status checks |

To start workers for specific queues:

```bash
# All queues (development)
celery -A celery_config worker -Q polling,booking,notifications,default -l info

# Separate workers (production)
celery -A celery_config worker -Q polling -l info --concurrency=2
celery -A celery_config worker -Q booking,default -l info --concurrency=4
celery -A celery_config worker -Q notifications -l info --concurrency=2

# Start the beat scheduler
celery -A celery_config beat -l info
```

### Verify It Works

```bash
# Check that the beat scheduler is running
celery -A celery_config inspect active

# Trigger a manual poll to test
celery -A celery_config call tasks.polling.poll_airbnb_bookings

# Check task results
celery -A celery_config result <task-id>
```

### Troubleshooting

- **Tasks not running?** Make sure both the worker AND beat processes are running. Beat schedules tasks; workers execute them.
- **Redis connection errors?** Verify `REDIS_URL` in `.env` and that Redis is running (`redis-cli ping`).
- **Timezone issues?** The scheduler uses `America/Los_Angeles` by default (set in `celery_config.py`). Change `timezone` if needed.

---

## 2. Adding Properties

Properties are the core entity — each property represents one rental unit (Airbnb listing, VRBO listing, etc.).

### Required Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | ✅ | — | Property name (e.g., "Luxury Strip View Apartment") |
| `location` | object | ✅ | — | `{ city, state, zip }` |
| `property_type` | string | | `"apartment"` | apartment, house, condo, etc. |
| `bedrooms` | int | | `1` | Number of bedrooms (0–20) |
| `bathrooms` | int | | `1` | Number of bathrooms (1–20) |
| `max_guests` | int | | `2` | Maximum guest capacity (1–50) |
| `airbnb_listing_id` | string | | `null` | Your Airbnb listing ID |
| `vrbo_listing_id` | string | | `null` | Your VRBO listing ID |
| `default_checkin_time` | time | | `15:00` | Default check-in time |
| `default_checkout_time` | time | | `11:00` | Default check-out time |
| `cleaning_budget` | float | | `150.00` | Default cleaning budget (USD) |
| `maintenance_budget` | float | | `200.00` | Default maintenance budget (USD) |
| `preferred_skills` | list | | `[]` | Preferred human skills (e.g., `["cleaning", "organizing"]`) |

### Option A: Add via Dashboard UI

1. Log in to the dashboard at `http://localhost:3000`
2. Navigate to **Properties** in the sidebar
3. Click **Add Property**
4. Fill in the property details (name, location, type, bedrooms, etc.)
5. Optionally enter your **Airbnb Listing ID** and/or **VRBO Listing ID** to enable automatic booking sync
6. Set your cleaning and maintenance budgets
7. Click **Save**

### Option B: Add via API

First, get an auth token:

```bash
# Register or login
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "yourpassword"}' \
  | jq -r '.access_token')
```

Create a property:

```bash
curl -X POST http://localhost:8000/api/properties/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Luxury Strip View Apartment",
    "location": {
      "city": "Las Vegas",
      "state": "NV",
      "zip": "89109"
    },
    "property_type": "apartment",
    "bedrooms": 2,
    "bathrooms": 2,
    "max_guests": 4,
    "airbnb_listing_id": "12345678",
    "default_checkin_time": "15:00",
    "default_checkout_time": "11:00",
    "cleaning_budget": 150.00,
    "maintenance_budget": 200.00,
    "preferred_skills": ["cleaning", "organizing"]
  }'
```

### Linking Airbnb/VRBO Listings

You can link platform listings at creation time (via `airbnb_listing_id` / `vrbo_listing_id`) or after the fact using the connect endpoints:

```bash
# Connect Airbnb listing
curl -X POST http://localhost:8000/api/properties/{property_id}/connect-airbnb \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"listing_id": "12345678"}'

# Connect VRBO listing
curl -X POST http://localhost:8000/api/properties/{property_id}/connect-vrbo \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"listing_id": "87654321"}'
```

**Where to find your listing IDs:**
- **Airbnb:** Go to your listing → the number in the URL (`airbnb.com/rooms/12345678`)
- **VRBO:** Go to your listing → the number in the URL (`vrbo.com/87654321`)

### iCal Import

> 🚧 **Coming soon:** iCal URL support for importing bookings from any calendar-based platform is planned. This will allow you to sync bookings from platforms beyond Airbnb and VRBO by providing an iCal feed URL.

### Seed Data for Testing

For development and testing, use the seed script to populate sample properties and bookings:

```bash
cd backend
python scripts/seed_data.py
```

This creates sample properties with mock bookings so you can test the full automation pipeline without real listings.

### Verify It Works

```bash
# List your properties
curl -s http://localhost:8000/api/properties/ \
  -H "Authorization: Bearer $TOKEN" | jq '.properties[] | {name, airbnb_listing_id}'

# Trigger a manual booking sync for a property
celery -A celery_config call tasks.polling.sync_property_bookings \
  --args='["<property-uuid>", "airbnb"]'
```

### Troubleshooting

- **"Property not found" errors?** Make sure you're using the correct `property_id` (UUID) and that the property belongs to your user.
- **Bookings not syncing?** Verify the `airbnb_listing_id` or `vrbo_listing_id` is correct and that polling tasks are running (see Section 1).
- **Location validation failing?** All three fields (`city`, `state`, `zip`) are required.

---

## 3. Notification Setup (SendGrid + Twilio)

The platform sends notifications for task lifecycle events: task created, human booked, task in progress, task completed, task failed, booking cancelled, and new guest bookings. A daily summary email is also sent each morning.

**If not configured, notifications fall back to logging** — you'll see `[EMAIL MOCK]` and `[SMS MOCK]` messages in the logs instead of actual emails/SMS. The platform works fine without them.

### SendGrid Setup (Email)

1. **Create a SendGrid account** at [https://signup.sendgrid.com](https://signup.sendgrid.com)

2. **Create an API key:**
   - Go to **Settings → API Keys → Create API Key**
   - Choose **Restricted Access** and enable **Mail Send** (Full Access)
   - Copy the key (you won't see it again)

3. **Verify a sender identity:**
   - Go to **Settings → Sender Authentication**
   - Either verify a single sender email or authenticate your domain (recommended for production)
   - The verified email must match your `SENDGRID_FROM_EMAIL`

4. **Set environment variables** in your `.env` file:

   ```bash
   SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   SENDGRID_FROM_EMAIL=notifications@yourdomain.com
   ```

📖 [SendGrid API Key Docs](https://docs.sendgrid.com/ui/account-and-settings/api-keys) | [Sender Authentication](https://docs.sendgrid.com/ui/account-and-settings/how-to-set-up-domain-authentication)

### Twilio Setup (SMS)

1. **Create a Twilio account** at [https://www.twilio.com/try-twilio](https://www.twilio.com/try-twilio)

2. **Get your credentials:**
   - From the Twilio Console dashboard, copy your **Account SID** and **Auth Token**

3. **Get a phone number:**
   - Go to **Phone Numbers → Manage → Buy a Number**
   - Choose a number with SMS capability
   - Copy the number (in E.164 format: `+1234567890`)

4. **Set environment variables** in your `.env` file:

   ```bash
   TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   TWILIO_AUTH_TOKEN=your_auth_token_here
   TWILIO_PHONE_NUMBER=+1234567890
   ```

> **Note:** On Twilio trial accounts, you can only send SMS to verified phone numbers. Add your number under **Phone Numbers → Verified Caller IDs** for testing.

📖 [Twilio Quickstart](https://www.twilio.com/docs/sms/quickstart/python) | [Console Dashboard](https://console.twilio.com)

### Notification Types

| Event | Email | SMS | When |
|-------|-------|-----|------|
| Task Created | ✅ | Optional | New cleaning/maintenance task generated from booking |
| Human Booked | ✅ | Optional | RentAHuman worker confirmed for task |
| Task In Progress | ✅ | Optional | Worker has started the task |
| Task Completed | ✅ | Optional | Task finished successfully |
| Task Failed | ✅ | Optional | Something went wrong |
| Booking Cancelled | ✅ | ✅ (urgent) | Worker cancelled — both channels for urgency |
| Daily Summary | ✅ | — | Morning digest at 8 AM |

The notification method (email, SMS, or both) is configured per-user via the Automation Config settings.

### Verify It Works

After setting the environment variables, restart the backend and check the logs:

```bash
# Restart to pick up new env vars
docker-compose restart backend

# Check logs for initialization messages
docker-compose logs backend | grep -i "sendgrid\|twilio"
# You should see: "SendGrid client initialized" and/or "Twilio client initialized"
```

Test by triggering a daily summary:

```bash
celery -A celery_config call tasks.notifications.send_daily_summary
```

### Troubleshooting

- **"SendGrid client initialized" not appearing?** Double-check `SENDGRID_API_KEY` is set and non-empty.
- **Emails not arriving?** Check your spam folder. Verify your sender identity in SendGrid. Check SendGrid's Activity Feed for delivery status.
- **Twilio "unverified number" error?** On trial accounts, you must verify recipient numbers first.
- **Still seeing `[EMAIL MOCK]` in logs?** The env vars aren't reaching the app — make sure `.env` is loaded and the service was restarted.

---

## 4. Stripe Payment Tracking

The platform tracks commissions on RentAHuman bookings at a **15% rate**. When a human is booked for a task, a payment record is created. Stripe integration enables real payment processing; without it, the system uses mock mode (records are tracked in the database but no real charges occur).

### How Commission Tracking Works

1. A human is booked for a task (e.g., cleaning at $150)
2. A payment record is created: `total_amount=$150.00`, `commission_amount=$22.50` (15%)
3. When the task completes, the payment record is marked as `PAID`
4. You can view commission summaries in the dashboard

### Stripe Setup

1. **Create a Stripe account** at [https://dashboard.stripe.com/register](https://dashboard.stripe.com/register)

2. **Get your API keys:**
   - Go to **Developers → API Keys**
   - Copy the **Secret key** (starts with `sk_test_` in test mode, `sk_live_` in production)
   - For testing, use the test mode keys (toggle "Test mode" in the Stripe dashboard)

3. **Set environment variables** in your `.env` file:

   ```bash
   STRIPE_SECRET_KEY=sk_test_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

4. **Set up the webhook endpoint:**
   - Go to **Developers → Webhooks → Add endpoint**
   - **Endpoint URL:** `https://yourdomain.com/api/webhooks/stripe`
     - For local development, use [Stripe CLI](https://stripe.com/docs/stripe-cli) to forward webhooks:
       ```bash
       stripe listen --forward-to localhost:8000/api/webhooks/stripe
       ```
       This will print a webhook signing secret (`whsec_...`) — use it as `STRIPE_WEBHOOK_SECRET`
   - **Events to subscribe to:**
     - `payment_intent.succeeded`
     - `payment_intent.payment_failed`

📖 [Stripe API Keys](https://stripe.com/docs/keys) | [Webhooks Guide](https://stripe.com/docs/webhooks) | [Stripe CLI](https://stripe.com/docs/stripe-cli)

### Testing with Stripe Test Mode

Stripe test mode lets you simulate payments without real money:

```bash
# Stripe CLI: trigger a test payment_intent.succeeded event
stripe trigger payment_intent.succeeded

# Or create a payment intent via the API
curl -X POST http://localhost:8000/api/payments/create-intent \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount": 150.00, "currency": "usd"}'
```

Use [Stripe test card numbers](https://stripe.com/docs/testing#cards):
- **Success:** `4242 4242 4242 4242`
- **Decline:** `4000 0000 0000 0002`
- **Requires auth:** `4000 0025 0000 3155`

### Commission Summary

View commission data via the dashboard or API:

```bash
curl -s http://localhost:8000/api/payments/commission-summary \
  -H "Authorization: Bearer $TOKEN" | jq
```

Example response:

```json
{
  "total_bookings": 12,
  "total_booking_value": 1800.00,
  "total_commission": 270.00,
  "pending_commission": 45.00,
  "paid_commission": 225.00,
  "average_booking_value": 150.00
}
```

### Verify It Works

```bash
# Restart to pick up Stripe env vars
docker-compose restart backend

# Check logs
docker-compose logs backend | grep -i stripe
# You should see: "Stripe client initialized"

# If using Stripe CLI for local webhooks:
stripe listen --forward-to localhost:8000/api/webhooks/stripe
# Then in another terminal:
stripe trigger payment_intent.succeeded
```

### Troubleshooting

- **"Stripe not configured" warning in logs?** `STRIPE_SECRET_KEY` is empty or not set. This is fine for development — mock mode tracks everything in the database.
- **Webhook signature errors?** Make sure `STRIPE_WEBHOOK_SECRET` matches the secret from `stripe listen` or your Stripe dashboard webhook config.
- **"Invalid webhook" 400 errors?** The signature doesn't match. In development mode, signature validation is relaxed, but double-check your `STRIPE_WEBHOOK_SECRET`.
- **Payment intents returning mock IDs (`pi_mock_...`)?** Stripe isn't configured — set `STRIPE_SECRET_KEY` for real payment processing.

---

## Next Steps

Once you've completed all four sections:

1. **Add your properties** and link your Airbnb/VRBO listing IDs
2. **Verify polling is working** by checking Celery worker logs for booking syncs
3. **Configure your automation preferences** in the dashboard (auto-book cleaning, maintenance, etc.)
4. **Set up notifications** so you're alerted when tasks are created and completed
5. **Monitor commissions** in the payments dashboard

For API reference, visit `http://localhost:8000/docs` (Swagger UI).
