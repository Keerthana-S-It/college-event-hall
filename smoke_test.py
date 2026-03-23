import os
import tempfile


fd, db_path = tempfile.mkstemp(prefix="college_event_smoke_", suffix=".db")
os.close(fd)
try:
    os.environ["SECRET_KEY"] = "smoke-test-secret"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

    from app import app  # noqa: E402
    from models import db, User, Hall, Booking  # noqa: E402
    from datetime import date, timedelta, time  # noqa: E402

    app.testing = True
    client = app.test_client()

    # Home and login page should be reachable
    r = client.get("/")
    assert r.status_code == 200, f"/ failed: {r.status_code}"
    r = client.get("/edumanage/login")
    assert r.status_code == 200, f"/edumanage/login failed: {r.status_code}"

    with app.app_context():
        # Create a sample staff user with mixed-case username
        u = User.query.filter_by(username="SmokeStaff").first()
        if u is None:
            u = User(username="SmokeStaff", full_name="Smoke Staff", role="staff")
            u.set_password("Smoke@123")
            db.session.add(u)
            db.session.commit()

        hall = Hall.query.first()
        assert hall is not None, "No hall found after init_db"

        # Create one fresh booking for report checks
        b = Booking(
            user_id=u.id,
            hall_id=hall.id,
            department="IT",
            booking_date=date.today(),
            num_days=1,
            start_time=time(0, 0),
            end_time=time(23, 59),
            purpose="Smoke test booking",
            chairs_required=10,
            guest_chairs=2,
            status="approved",
        )
        db.session.add(b)
        db.session.commit()

    # Case-insensitive login check
    r = client.post(
        "/edumanage/login",
        data={"username": "smokestaff", "password": "Smoke@123"},
        follow_redirects=False,
    )
    assert r.status_code in (302, 303), f"staff login failed: {r.status_code}"

    # Admin login for reports
    client.get("/edumanage/logout")
    r = client.post(
        "/edumanage/login",
        data={"username": "admin", "password": "Admin@grdcs"},
        follow_redirects=False,
    )
    assert r.status_code in (302, 303), f"admin login failed: {r.status_code}"

    start = (date.today() - timedelta(days=1)).isoformat()
    end = (date.today() + timedelta(days=1)).isoformat()

    # Reports HTML, PDF, Excel should work
    r = client.get(f"/admin/reports/monthly?from_date={start}&to_date={end}&status=all&format=html")
    assert r.status_code == 200, f"report html failed: {r.status_code}"
    assert b"Hall Usage Report" in r.data, "report html missing content"

    r = client.get(f"/admin/reports/monthly?from_date={start}&to_date={end}&status=all&format=pdf")
    assert r.status_code == 200, f"report pdf failed: {r.status_code}"
    assert r.headers.get("Content-Type", "").startswith("application/pdf"), "pdf content-type invalid"

    r = client.get(f"/admin/reports/monthly?from_date={start}&to_date={end}&status=all&format=excel")
    assert r.status_code == 200, f"report excel failed: {r.status_code}"
    assert "spreadsheetml" in r.headers.get("Content-Type", ""), "excel content-type invalid"

    print("SMOKE_TEST_OK")
finally:
    try:
        os.remove(db_path)
    except OSError:
        pass
