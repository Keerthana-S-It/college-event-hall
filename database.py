from models import db, User, Hall, Booking, Keyword, HALL_NAMES, Notification, Block
from sqlalchemy import text

def init_db(app):
    with app.app_context():
        db.create_all()
        # Lightweight SQLite-only "migration" for older local DBs.
        # For PostgreSQL/MySQL/etc., use proper migrations (Alembic/Flask-Migrate).
        if db.engine.dialect.name == "sqlite":
            try:
                cols = db.session.execute(text("PRAGMA table_info(bookings)")).all()
                existing = {row[1] for row in cols}  # row[1] is column name

                # column_name -> SQLite column DDL (type + optional DEFAULT)
                needed = {
                    "faculties_count": "INTEGER DEFAULT 0",
                    "audio_system": "INTEGER DEFAULT 0",
                    "microphones": "INTEGER DEFAULT 0",
                    "mic_types": "TEXT DEFAULT ''",
                    "photography": "INTEGER DEFAULT 0",
                    "podium_required": "INTEGER DEFAULT 0",
                    "created_at": "DATETIME",
                    "cancellation_reason": "TEXT",
                    "cancelled_at": "DATETIME",
                    "admin_notes": "TEXT",
                }
                for name, ddl in needed.items():
                    if name not in existing:
                        db.session.execute(text(f"ALTER TABLE bookings ADD COLUMN {name} {ddl}"))

                # Backfill defaults
                db.session.execute(text("UPDATE bookings SET faculties_count = 0 WHERE faculties_count IS NULL"))
                db.session.execute(text("UPDATE bookings SET audio_system = 0 WHERE audio_system IS NULL"))
                db.session.execute(text("UPDATE bookings SET microphones = 0 WHERE microphones IS NULL"))
                db.session.execute(text("UPDATE bookings SET mic_types = '' WHERE mic_types IS NULL"))
                db.session.execute(text("UPDATE bookings SET photography = 0 WHERE photography IS NULL"))
                db.session.execute(text("UPDATE bookings SET podium_required = 0 WHERE podium_required IS NULL"))
                # Migrate old 'active' status to 'approved' for approval workflow
                db.session.execute(text("UPDATE bookings SET status = 'approved' WHERE status = 'active'"))
                db.session.commit()
            except Exception:
                db.session.rollback()

            try:
                ucols = db.session.execute(text("PRAGMA table_info(users)")).all()
                uexisting = {row[1] for row in ucols}
                if "email" not in uexisting:
                    db.session.execute(text("ALTER TABLE users ADD COLUMN email TEXT"))
                if "full_name" not in uexisting:
                    db.session.execute(text("ALTER TABLE users ADD COLUMN full_name TEXT"))
                if "password_plain" not in uexisting:
                    db.session.execute(text("ALTER TABLE users ADD COLUMN password_plain TEXT"))
                db.session.commit()
            except Exception:
                # If anything goes wrong here, app can still run; schema issues will surface clearly.
                db.session.rollback()
        # Rename hall if older name exists
        old = Hall.query.filter_by(name='Kailah hall').first()
        if old is not None and Hall.query.filter_by(name='Kailash hall').first() is None:
            old.name = 'Kailash hall'
        # Create default halls if not exist, with specific capacities
        capacities = {
            'RD hall': 600,
            'AV hall': 70,
            'Kailash hall': 2000,
            'Charles Babbage hall': 700,
            'IM hall': 100,
        }
        for name in HALL_NAMES:
            hall = Hall.query.filter_by(name=name).first()
            if hall is None:
                hall = Hall(name=name, capacity=capacities.get(name, Hall.capacity.property.columns[0].default.arg or 200))
                db.session.add(hall)
            else:
                # keep DB in sync with configured capacities
                if name in capacities:
                    hall.capacity = capacities[name]

        # Create fixed blocks if not exist
        for bn in ['IT block', 'IM block', 'SCIB block', 'MAIN block']:
            if Block.query.filter_by(name=bn).first() is None:
                db.session.add(Block(name=bn))
        # Default admin user (username: admin, password: Admin@grdcs)
        admin_user = User.query.filter_by(username='admin').first()
        legacy_admin = User.query.filter_by(username='admingrdcs').first()
        if admin_user is None and legacy_admin is not None:
            # Preserve existing admin account (ID/bookings) and just rename credentials.
            legacy_admin.username = 'admin'
            legacy_admin.role = 'admin'
            if not legacy_admin.full_name:
                legacy_admin.full_name = 'GRDCS Admin'
            legacy_admin.set_password('Admin@grdcs')
        elif admin_user is None and legacy_admin is None:
            admin = User(username='admin', role='admin', full_name='GRDCS Admin')
            admin.set_password('Admin@grdcs')
            db.session.add(admin)
        else:
            # Ensure password matches configured default (optional hardening).
            admin_user.role = 'admin'
            if not admin_user.full_name:
                admin_user.full_name = 'GRDCS Admin'
            admin_user.set_password('Admin@grdcs')
        # Default staff user (password: staff123)
        staff_user = User.query.filter_by(username='staff').first()
        if staff_user is None:
            u = User(username='staff', role='staff')
            u.set_password('staff123')
            u.password_plain = 'staff123'
            db.session.add(u)
        else:
            # Backfill plain password for older DBs (cannot recover other users' old passwords)
            if getattr(staff_user, "password_plain", None) in (None, ''):
                staff_user.password_plain = 'staff123'
        # Legacy staff (password: user123) - kept for existing bookings
        legacy_user = User.query.filter_by(username='user').first()
        if legacy_user is None:
            u = User(username='user', role='staff')
            u.set_password('user123')
            u.password_plain = 'user123'
            db.session.add(u)
        else:
            if getattr(legacy_user, "password_plain", None) in (None, ''):
                legacy_user.password_plain = 'user123'
        db.session.commit()
