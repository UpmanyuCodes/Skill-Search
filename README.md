# Skill Search

A Django web app that connects people with **verified local service providers**: plumbers, electricians, home tutors, carpenters, AC repair, cleaners, mechanics, beauticians, cooks, drivers and more.

- **Service providers** register, upload a government ID and are listed once an admin verifies them.
- **Customers** search by service, keyword, city/pincode or live location, compare ratings, prices and distance, then contact the provider.

## Features

**For customers**
- Search by keyword, category, city/pincode or "near me" (browser geolocation + distance radius)
- Filters: minimum rating, max price, available now, emergency service, home visit
- Sort by best match, nearest, rating, price, experience
- Map of results (Leaflet + OpenStreetMap, no API key needed)
- Live in-app chat that updates without reloading
- Several ways to get in touch: phone call, WhatsApp, email, in-app chat, booking request
- Booking requests with date, time, address and an "urgent" flag; track and cancel them on the dashboard
- Reviews and star ratings, only allowed after a completed booking (one per job)
- Save favourite providers, share profiles, report suspicious profiles

**For service providers**
- Sign up as a provider, or turn an existing customer account into one
- Profile: skills, experience, prices (per hour/visit/day/session/month), languages, working hours, service area and travel radius
- ID verification: Aadhaar / PAN / Voter ID / Driving licence / Passport upload (only the last 4 ID digits are stored)
- Dashboard: accept, decline and complete jobs, reply to messages, see views, ratings and saves
- One-click "Available / Busy" switch

**Admin** (`/admin/`)
- Approve, reject or reset provider verification in bulk, and open uploaded documents
- Manage categories, bookings, reviews, reports and conversations

**Testing mode**
- `/testing/` creates instantly verified test providers (random or custom name, category, city, or near your location) and lets you approve pending sign-ups in one click
- `python manage.py seed_demo` fills the site with providers, customers, bookings and reviews
- Test mode is **on when `DJANGO_DEBUG` is on** and turns off automatically in production, where ID documents become mandatory

**JSON API**
- `GET /api/providers/?q=&category=&city=&lat=&lng=&radius=&min_rating=&sort=&limit=`
- `GET /api/categories/`

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (source .venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo      # optional demo data
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000.

Demo logins after `seed_demo`:
- Customer: `demo` / `demo12345` (located in Delhi)
- Any provider: their username / `testpass123`

Run the tests with `python manage.py test`.

## Configuration (environment variables)

| Variable | Default | Purpose |
|---|---|---|
| `DJANGO_DEBUG` | `True` | Debug mode |
| `DJANGO_SECRET_KEY` | dev key | **Set this in production** |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma separated |
| `SKILLSEARCH_TEST_MODE` | same as debug | Enables `/testing/` and makes ID upload optional |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST` | not set | Use PostgreSQL instead of SQLite (needs `pip install psycopg`) |

## Project layout

```
accounts/   custom User (customer/provider role), signup, login, profile, dashboard
services/   categories, provider profiles, search, bookings, reviews, chat, favourites, reports, API
templates/  Bootstrap 5 templates
static/     CSS and JS (geolocation, saving favourites, sharing)
```
