import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'instance', 'event_booking.db')


def _normalize_database_url(url: str) -> str:
    """Convert provider URLs into SQLAlchemy-compatible URLs."""
    if not url:
        return url
    # Render/Heroku often expose postgres://, while SQLAlchemy expects postgresql://
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'edu-manage-event-booking-secret-key'
    # Use absolute path so SQLite can always open the existing DB
    SQLALCHEMY_DATABASE_URI = _normalize_database_url(os.environ.get('DATABASE_URL')) or f"sqlite:///{DB_PATH}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Email settings removed – application no longer sends emails.
