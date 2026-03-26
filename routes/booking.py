from datetime import date, time, datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
from models import db, User, Hall, Booking, Notification
import holidays

booking_bp = Blueprint('booking', __name__)

def _parse_date_flexible(s: str):
    """Accept both HTML date input (YYYY-MM-DD) and DD-MM-YYYY."""
    s = (s or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            continue
    return None

def _fmt_ddmmyyyy(d):
    try:
        return d.strftime("%d-%m-%Y") if d else ""
    except Exception:
        return ""

def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please log in to continue.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return wrapped

def admin_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please log in.', 'error')
            return redirect(url_for('auth.login'))
        if session.get('role') != 'admin':
            flash('Admin access required.', 'error')
            return redirect(url_for('booking.dashboard'))
        return f(*args, **kwargs)
    return wrapped


@booking_bp.route('/edumanage/dashboard')
@login_required
def dashboard():
    halls = Hall.query.all()
    return render_template('dashboard.html', halls=halls)


@booking_bp.route('/edumanage/notifications', methods=['GET', 'POST'])
@login_required
def notifications():
    if request.method == 'POST':
        # Mark all as read
        Notification.query.filter_by(user_id=session.get('user_id'), is_read=False).update({"is_read": True})
        db.session.commit()
        flash('Notifications marked as read.', 'success')
        return redirect(url_for('booking.notifications'))
    items = Notification.query.filter_by(user_id=session.get('user_id')).order_by(Notification.created_at.desc()).all()
    return render_template('notifications.html', notifications=items)


@booking_bp.route('/edumanage/book/<int:hall_id>', methods=['GET', 'POST'])
@login_required
def book_hall(hall_id):
    hall = Hall.query.get_or_404(hall_id)
    staff_users = User.query.filter(User.role.in_(['staff', 'user', 'admin'])).order_by(User.username).all() if session.get('role') == 'admin' else []
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        if request.is_json:
            department = (data.get('department') or '').strip()
        else:
            department = (request.form.get('department') or '').strip()
        start_date_s = data.get('start_date') or ''
        end_date_s = data.get('end_date') or ''
        purpose = (data.get('purpose') or '').strip()
        chairs_required = data.get('chairs_required')
        guest_chairs = data.get('guest_chairs')
        faculties_count = data.get('faculties_count')
        audio_system = data.get('audio_system')
        microphones = data.get('microphones')
        if request.is_json:
            mic_types_raw = data.get('mic_types') or ''
        else:
            mic_types_raw = request.form.get('mic_types') or ''
        photography = data.get('photography')
        podium_required = data.get('podium_required')

        # Validations
        errors = []
        if not department:
            errors.append('Department is mandatory.')
        start_date = _parse_date_flexible(start_date_s)
        if not start_date:
            errors.append('Invalid start date.')
        end_date = _parse_date_flexible(end_date_s)
        if not end_date:
            errors.append('Invalid end date.')

        if start_date and start_date < date.today():
            errors.append('Past dates are not allowed.')
        if start_date and end_date:
            if end_date < start_date:
                errors.append('End date must be the same as or after start date.')
            num_days = (end_date - start_date).days + 1
            if num_days <= 0:
                errors.append('Number of days must be greater than 0.')
            else:
                # Do not allow bookings on Tamil Nadu government leave days.
                years = {start_date.year, end_date.year}
                holiday_maps = {y: holidays.country_holidays("IN", subdiv="TN", years=y) for y in years}
                for i in range(num_days):
                    d = start_date + timedelta(days=i)
                    hmap = holiday_maps.get(d.year)
                    if hmap and d in hmap:
                        errors.append(f'Booking is not allowed on leave day: {_fmt_ddmmyyyy(d)} ({hmap.get(d)}).')
                        break
        else:
            num_days = 0
        # Time selection removed from UI; treat every booking as full-day.
        start_time = time(0, 0)
        end_time = time(23, 59)
        if not purpose:
            errors.append('Purpose of booking is mandatory.')
        try:
            chairs_required = int(chairs_required) if chairs_required not in (None, '') else 0
        except (TypeError, ValueError):
            chairs_required = 0
        if chairs_required < 0:
            errors.append('Chairs required must be valid.')
        if chairs_required > hall.capacity:
            errors.append('Chairs required must not exceed hall capacity ({0}).'.format(hall.capacity))
        try:
            faculties_count = int(faculties_count) if faculties_count not in (None, '') else 0
        except (TypeError, ValueError):
            faculties_count = 0
        if faculties_count < 0:
            errors.append('Number of faculties must be valid.')
        try:
            guest_chairs = int(guest_chairs) if guest_chairs not in (None, '') else 0
        except (TypeError, ValueError):
            guest_chairs = 0
        if guest_chairs > hall.capacity:
            errors.append('Guest chairs must not exceed total available capacity ({0}).'.format(hall.capacity))
        audio_yes = str(audio_system).lower() in ('yes', 'true', '1')
        if audio_yes:
            # Parse mic_types as "neck_band:2,hand:3,fixed:1" or use microphones from form
            microphones = 0
            selected_types = []
            if mic_types_raw and ':' in str(mic_types_raw):
                for part in str(mic_types_raw).split(','):
                    part = part.strip()
                    if ':' in part:
                        name, cnt = part.split(':', 1)
                        try:
                            n = int(cnt.strip())
                            if n > 0 and name.strip():
                                microphones += n
                                selected_types.append(part.strip())
                        except (TypeError, ValueError):
                            pass
            else:
                try:
                    microphones = int(microphones) if microphones not in (None, '') else 0
                except (TypeError, ValueError):
                    microphones = 0
            if microphones <= 0:
                errors.append('Enter quantity for at least one microphone type when Audio System is Yes.')
        else:
            microphones = 0
            selected_types = []
        photo_yes = str(photography).lower() in ('yes', 'true', '1')
        podium_yes = str(podium_required).lower() in ('yes', 'true', '1')

        if errors:
            if request.is_json:
                return jsonify({'success': False, 'errors': errors}), 400
            for e in errors:
                flash(e, 'error')
            return redirect(url_for('booking.book_hall', hall_id=hall_id))

        # Conflict detection: check overlap with approved bookings only
        for d in range(num_days):
            check_date = start_date + timedelta(days=d)
            overlap = Booking.query.filter(
                Booking.hall_id == hall_id,
                Booking.status == 'approved',
                Booking.booking_date == check_date
            ).first()
            if overlap:
                if request.is_json:
                    return jsonify({
                        'success': False,
                        'errors': ['This slot is already booked. Please choose another date/time.']
                    }), 400
                flash('This slot is already booked. Please choose another date/time.', 'error')
                return redirect(url_for('booking.book_hall', hall_id=hall_id))

        b = Booking(
            user_id=session['user_id'],
            hall_id=hall_id,
            department=department,
            booking_date=start_date,
            num_days=num_days,
            start_time=start_time,
            end_time=end_time,
            purpose=purpose,
            chairs_required=chairs_required,
            guest_chairs=guest_chairs,
            faculties_count=faculties_count,
            audio_system=audio_yes,
            microphones=microphones,
            mic_types=",".join(selected_types) if audio_yes else "",
            photography=photo_yes,
            podium_required=podium_yes,
            status='pending',
        )
        db.session.add(b)
        db.session.commit()
        if request.is_json:
            return jsonify({'success': True, 'message': 'Booking confirmed.', 'id': b.id})
        flash('Booking confirmed.', 'success')
        return redirect(url_for('booking.my_bookings'))
    return render_template(
        'book_hall.html',
        hall=hall,
        staff_users=staff_users,
    )


@booking_bp.route('/edumanage/my-bookings')
@login_required
def my_bookings():
    # Show all bookings for all logged-in roles.
    bookings = Booking.query.order_by(Booking.booking_date.desc(), Booking.created_at.desc()).all()
    return render_template('my_bookings.html', bookings=bookings)


@booking_bp.route('/edumanage/cancel-booking/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    b = Booking.query.get_or_404(booking_id)
    reason = (request.form.get('cancellation_reason') or '').strip()
    if not reason:
        flash('Cancellation reason is required.', 'error')
        return redirect(url_for('booking.my_bookings'))
    b.status = 'cancelled'
    b.cancellation_reason = reason
    b.cancelled_at = datetime.utcnow()
    db.session.commit()
    flash('Booking cancelled successfully.', 'success')
    return redirect(url_for('booking.my_bookings'))


@booking_bp.route('/edumanage/availability')
@login_required
def availability():
    hall_id = request.args.get('hall_id', type=int)
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    if not hall_id or not from_date:
        return jsonify({'booked_slots': []})
    from_d = _parse_date_flexible(from_date)
    if not from_d:
        return jsonify({'booked_slots': []})
    to_d = _parse_date_flexible(to_date) if to_date else from_d
    if not to_d:
        to_d = from_d
    # Include approved and pending (approved blocks conflicts; show both for availability)
    slots = Booking.query.filter(
        Booking.hall_id == hall_id,
        Booking.status.in_(['approved', 'pending']),
        Booking.booking_date <= to_d
    ).all()
    booked_slots = []
    for s in slots:
        booking_start = s.booking_date
        booking_end = s.booking_date + timedelta(days=max((s.num_days or 1) - 1, 0))
        if booking_end < from_d:
            continue
        # expand each day (so UI sees exact booked days)
        days = max(s.num_days or 1, 1)
        for i in range(days):
            d = booking_start + timedelta(days=i)
            if d < from_d or d > to_d:
                continue
            booked_slots.append({
                'date': d.isoformat(),
                'start': s.start_time.strftime('%H:%M'),
                'end': s.end_time.strftime('%H:%M'),
                'purpose': (s.purpose or '')[:50],
                'status': s.status
            })
    booked_slots.sort(key=lambda x: (x['date'], x['start'], x['end']))
    return jsonify({'booked_slots': booked_slots})


@booking_bp.route('/edumanage/calendar-data')
@login_required
def calendar_data():
    """Return all bookings for a given month/year grouped by day, for the dashboard calendar."""
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    hall_id = request.args.get('hall_id', type=int)
    today = date.today()
    if not year or not month:
        year, month = today.year, today.month
    first = date(year, month, 1)
    if month == 12:
        last = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last = date(year, month + 1, 1) - timedelta(days=1)
    # Fetch bookings that start within or before this month; then expand days in Python.
    # Dashboard calendar should NOT highlight cancelled dates, so exclude cancelled bookings.
    visible_statuses = ["approved", "pending", "rejected"]
    q = Booking.query.filter(
        Booking.booking_date <= last,
        Booking.status.in_(visible_statuses)
    )
    if hall_id:
        q = q.filter(Booking.hall_id == hall_id)
    bookings = q.all()
    by_date = {}
    for b in bookings:
        days = max(int(b.num_days or 1), 1)
        for i in range(days):
            d = b.booking_date + timedelta(days=i)
            if d < first or d > last:
                continue
            key = d.isoformat()
            by_date.setdefault(key, []).append({
                "hall": b.hall.name if b.hall else "",
                "start": b.start_time.strftime("%H:%M"),
                "end": b.end_time.strftime("%H:%M"),
                "purpose": (b.purpose or "")[:80],
                "status": b.status,
                "is_mine": (b.user_id == session.get('user_id')),
            })
    # Sort bookings within each day
    for k in by_date:
        by_date[k].sort(key=lambda x: (x["start"], x["end"], x["hall"]))
    tn_holidays = holidays.country_holidays("IN", subdiv="TN", years=year)
    gov_holidays = {}
    for dt, name in tn_holidays.items():
        if first <= dt <= last:
            gov_holidays[dt.isoformat()] = str(name)
    return jsonify({
        "year": year,
        "month": month,
        "hall_id": hall_id,
        "bookings_by_date": by_date,
        "gov_holidays": gov_holidays,
    })


@booking_bp.route('/edumanage/tn-holidays')
@login_required
def tn_holidays():
    """Return Tamil Nadu government holidays for a given year."""
    year = request.args.get('year', type=int)
    if not year:
        year = date.today().year
    hmap = holidays.country_holidays("IN", subdiv="TN", years=year)
    return jsonify({
        "year": year,
        "holidays": {dt.isoformat(): str(name) for dt, name in hmap.items()}
    })


@booking_bp.route('/edumanage/check-availability')
@login_required
def check_availability():
    """Real-time conflict check for selected date/time range. Returns available=True/False."""
    hall_id = request.args.get('hall_id', type=int)
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    start_time_s = request.args.get('start_time')
    end_time_s = request.args.get('end_time')
    if not hall_id or not from_date or not start_time_s or not end_time_s:
        return jsonify({'available': True, 'message': 'Incomplete data'})
    try:
        from_d = _parse_date_flexible(from_date)
        to_d = _parse_date_flexible(to_date or from_date)
        if not from_d or not to_d:
            raise ValueError("Invalid date")
        start_time = datetime.strptime(start_time_s, '%H:%M').time()
        end_time = datetime.strptime(end_time_s, '%H:%M').time()
    except Exception:
        return jsonify({'available': True, 'message': 'Invalid date/time'})
    if end_time <= start_time:
        return jsonify({'available': False, 'message': 'End time must be after start time'})
    num_days = (to_d - from_d).days + 1
    for d in range(num_days):
        check_date = from_d + timedelta(days=d)
        overlap = Booking.query.filter(
            Booking.hall_id == hall_id,
            Booking.status == 'approved',
            Booking.booking_date == check_date,
            Booking.start_time < end_time,
            Booking.end_time > start_time
        ).first()
        if overlap:
            return jsonify({'available': False, 'message': 'Slot conflicts with an approved booking'})
    return jsonify({'available': True, 'message': 'Slot is available'})


@booking_bp.route('/edumanage/print/<int:booking_id>')
@login_required
def print_booking(booking_id):
    """Print-friendly booking sheet for letterhead/Xerox."""
    b = Booking.query.get_or_404(booking_id)
    return render_template('print_booking.html', booking=b)
