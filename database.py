from models import db, User, Hall, Booking, Keyword, HALL_NAMES, Notification, Block
from sqlalchemy import text


def init_db(app):
    with app.app_context():
        # ✅ Create all tables (works for Neon + SQLite)
        db.create_all()

        # ✅ Run SQLite-only migrations (skip for Neon/PostgreSQL)
        if db.engine.dialect.name == "sqlite":
            try:
                cols = db.session.execute(text("PRAGMA table_info(bookings)")).all()
                existing = {row[1] for row in cols}

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

                db.session.commit()
            except Exception as e:
                print("SQLite migration error:", e)
                db.session.rollback()

        # ✅ Fix hall name typo
        old = Hall.query.filter_by(name='Kailah hall').first()
        if old and not Hall.query.filter_by(name='Kailash hall').first():
            old.name = 'Kailash hall'

        # ✅ Default hall setup
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
                hall = Hall(
                    name=name,
                    capacity=capacities.get(name, 200)
                )
                db.session.add(hall)
            else:
                if name in capacities:
                    hall.capacity = capacities[name]

        # ✅ Blocks
        for bn in ['IT block', 'IM block', 'SCIB block', 'MAIN block']:
            if not Block.query.filter_by(name=bn).first():
                db.session.add(Block(name=bn))

        # ✅ Admin user
        admin_user = User.query.filter_by(username='admin').first()

        if admin_user is None:
            admin = User(username='admin', role='admin', full_name='GRDCS Admin')
            admin.set_password('Admin@grdcs')
            db.session.add(admin)
        else:
            admin_user.role = 'admin'
            if not admin_user.full_name:
                admin_user.full_name = 'GRDCS Admin'

        # ✅ Staff user
        staff_user = User.query.filter_by(username='staff').first()
        if staff_user is None:
            u = User(username='staff', role='staff')
            u.set_password('staff123')
            u.password_plain = 'staff123'
            db.session.add(u)

        # ✅ Legacy user
        legacy_user = User.query.filter_by(username='user').first()
        if legacy_user is None:
            u = User(username='user', role='staff')
            u.set_password('user123')
            u.password_plain = 'user123'
            db.session.add(u)

        # ✅ Final commit
        try:
            db.session.commit()
        except Exception as e:
            print("DB commit error:", e)
            db.session.rollback()