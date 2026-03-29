import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'instance', 'event_booking.db')


def _normalize_database_url(url: str) -> str:
    """Convert provider URLs into SQLAlchemy-compatible URLs."""
    if not url:
        return url

    # Fix for Render / Heroku old format
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]

    return url


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'edu-manage-event-booking-secret-key')

    # ✅ Use Neon DB if available, else fallback to SQLite (for local only)
    database_url = _normalize_database_url(os.environ.get('DATABASE_URL'))

    if database_url:
        SQLALCHEMY_DATABASE_URI = database_url
    else:
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{DB_PATH}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ✅ Important for Neon (prevents connection timeout issues)
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }