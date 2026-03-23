# EduManage – Event Hall Booking

Event hall booking system with login, hall selection, and admin keyword management.

## Features

- **Login** at `/edumanage/login` (EduManage)
- **Halls:** RD hall, Charles Babbage hall, Kailah hall, AV hall
- **Booking form:** Department/Year (dropdown + optional custom), Date (current/future only; past disabled), Number of days (> 0), Start/End time (end > start), Purpose (required), Chairs & Guest chairs (guest ≤ capacity), Audio system (Yes/No), Microphones (required if Audio = Yes), Photography (Yes/No)
- **Already booked:** “Show already booked slots” opens a popup with booked slots for the selected date range
- **Cancellation:** Cancel from “My Bookings”; cancelled bookings are removed from the active list
- **Admin:** Manage keywords at `/admin/keywords` (admin only)

## Setup

```bash
cd "e:\Projects\college event"
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000

## Deploy on Render (PostgreSQL)

- This project supports Render PostgreSQL through `DATABASE_URL`.
- `config.py` automatically converts `postgres://...` to `postgresql://...` for SQLAlchemy.
- Deploy using the included `render.yaml` (Blueprint deploy):
  - Web service start command: `gunicorn app:app`
  - Database: managed PostgreSQL (`college-event-db`)
  - Required env vars: `SECRET_KEY`, `DATABASE_URL` (auto-wired by `render.yaml`)

## Default logins

- **Admin:** username `admin`, password `Admin@grdcs`
- **User:** username `user`, password `user123`

## Tech stack

- Backend: Python, Flask
- Database: SQLite (file: `instance/event_booking.db`)
- Frontend: HTML, CSS, minimal JS
