# How to Run the Event Hall Booking System

## Quick Start

### Step 1: Install Dependencies
Open PowerShell or Command Prompt in the project folder and run:
```bash
pip install -r requirements.txt
```

**If you get SQLAlchemy errors with Python 3.13**, upgrade SQLAlchemy:
```bash
pip install --upgrade SQLAlchemy
```

### Step 2: Run the Application
```bash
python app.py
```

### Step 3: Access the Application
Open your web browser and go to:
```
http://127.0.0.1:5000
```

You will be redirected to the login page at:
```
http://127.0.0.1:5000/edumanage/login
```

## Default Login Credentials

**Admin Account:**
- Username: `admin`
- Password: `Admin@grdcs`

**Regular User Account:**
- Username: `user`
- Password: `user123`

## Troubleshooting

### SQLAlchemy Error with Python 3.13
If you see an error like:
```
AssertionError: Class <class 'sqlalchemy.sql.elements.SQLCoreOperations'>...
```

**Solution:** Upgrade SQLAlchemy to the latest version:
```bash
pip install --upgrade SQLAlchemy
```

Or use Python 3.11 or 3.12 instead of 3.13.

### Port Already in Use
If port 5000 is already in use, edit `app.py` and change:
```python
app.run(debug=True, port=5000)
```
to a different port (e.g., `port=5001`).

### Database File
- Local SQLite database is created at `instance/event_booking.db` when running without `DATABASE_URL`.
- On Render, PostgreSQL is used automatically via `DATABASE_URL`.

## Features Available

1. **Login** - Use credentials above
2. **Dashboard** - View available halls
3. **Book Hall** - Fill out booking form with all validations
4. **My Bookings** - View and cancel your bookings
5. **Admin Keywords** - (Admin only) Manage keywords
