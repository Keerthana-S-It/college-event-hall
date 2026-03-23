from flask import Flask, request, redirect, url_for, session
from config import Config
from models import db
from database import init_db

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
init_db(app)

# Import routes after app is created
from routes import auth_bp, booking_bp, admin_bp
app.register_blueprint(auth_bp, url_prefix='/')
app.register_blueprint(booking_bp, url_prefix='/booking')
app.register_blueprint(admin_bp, url_prefix='/admin')


@app.route('/')
def index():
    from flask import redirect, session, url_for, render_template
    if session.get('user_id'):
        return redirect(url_for('booking.dashboard'))
    return render_template('home.html')


if __name__ == '__main__':
    app.run(debug=True, port=5000)
