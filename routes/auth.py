from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from sqlalchemy import func
from models import db, User
from functools import wraps

auth_bp = Blueprint('auth', __name__)


def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please log in to continue.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return wrapped


@auth_bp.route('/edumanage/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if not username or not password:
            flash('Username and password are required.', 'error')
            return render_template('login.html')
        username_norm = " ".join(username.split())
        # 1) Primary lookup by username (case-insensitive)
        user = User.query.filter(func.lower(User.username) == username_norm.lower()).first()
        # 2) Fallback for staff: allow login using faculty name as entered in Create Staff.
        #    This helps existing users who type the display name instead of login ID.
        if user is None:
            user = User.query.filter(
                User.role == 'staff',
                User.full_name.isnot(None),
                func.lower(User.full_name) == username_norm.lower(),
            ).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            flash('Logged in successfully.', 'success')
            return redirect(url_for('booking.dashboard'))
        flash('Invalid username or password.', 'error')
    return render_template('login.html')


@auth_bp.route('/edumanage/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))


@auth_bp.route('/edumanage/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Legacy route kept to avoid errors if bookmarked; now just redirects to dashboard."""
    flash('Profile editing has been disabled by the administrator.', 'info')
    return redirect(url_for('booking.dashboard'))
