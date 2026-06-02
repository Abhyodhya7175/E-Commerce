from datetime import datetime

from flask import Blueprint, jsonify, redirect, render_template, request, url_for, flash
from flask_login import login_required, login_user, logout_user

from ..extensions import db
from ..models import User
from ..services.otp import (
    MailDeliveryError,
    MailNotConfiguredError,
    create_and_send_otp,
    mail_config_hint,
    mail_is_configured,
    verify_otp,
)
from ..shop_state import merge_guest_state_into_user

auth_bp = Blueprint('auth', __name__)


def _redirect_after_login(user):
    if user.role == 'admin':
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('customer.shop_home'))


def _login_user_session(user):
    user.last_login = datetime.utcnow()
    user.is_verified = True
    db.session.commit()
    login_user(user)
    merge_guest_state_into_user(user.id)


def _complete_login(user):
    _login_user_session(user)
    return _redirect_after_login(user)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        email = (request.form.get('email') or '').strip().lower()
        password = (request.form.get('password') or '').strip()
        otp = (request.form.get('otp') or '').strip()

        if not name or not email:
            flash('Name and email are required.', 'danger')
            return redirect(url_for('auth.register'))
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('auth.register'))
        if not otp:
            flash('Enter the verification code sent to your email.', 'danger')
            return redirect(url_for('auth.register'))
        if not verify_otp(email, otp):
            flash('Invalid or expired verification code.', 'danger')
            return redirect(url_for('auth.register'))
        if password and len(password) < 6:
            flash('Password must be at least 6 characters if you set one.', 'danger')
            return redirect(url_for('auth.register'))

        user = User(name=name, email=email, role='customer', is_verified=True)
        if password:
            user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful. You can sign in now.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        password = (request.form.get('password') or '').strip()
        selected_role = request.form.get('role', 'customer')
        user = User.query.filter_by(email=email).first()

        if not user:
            flash('No account found for this email.', 'danger')
            return redirect(url_for('auth.login'))
        if not user.has_password:
            flash('This account uses email code sign-in. Switch to the Email Code tab.', 'danger')
            return redirect(url_for('auth.login'))
        if not password:
            flash('Enter your password or use email code sign-in.', 'danger')
            return redirect(url_for('auth.login'))
        if not user.check_password(password):
            flash('Invalid credentials', 'danger')
            return redirect(url_for('auth.login'))
        if user.role != selected_role:
            flash('Selected role does not match this account.', 'danger')
            return redirect(url_for('auth.login'))
        return _complete_login(user)
    return render_template('auth/login.html')


@auth_bp.route('/otp/send', methods=['POST'])
def send_otp():
    data = request.get_json(silent=True) or request.form
    email = (data.get('email') or '').strip().lower()
    purpose = (data.get('purpose') or 'login').strip().lower()

    if not email or '@' not in email:
        return jsonify(ok=False, error='Enter a valid email address.'), 400

    if purpose == 'login':
        if not User.query.filter_by(email=email).first():
            return jsonify(ok=False, error='No account found. Create an account first.'), 404
    elif purpose == 'register':
        if User.query.filter_by(email=email).first():
            return jsonify(ok=False, error='Email already registered.'), 409
    else:
        return jsonify(ok=False, error='Invalid request.'), 400

    if not mail_is_configured():
        return jsonify(ok=False, error=mail_config_hint()), 503

    try:
        create_and_send_otp(email, purpose)
    except MailNotConfiguredError as exc:
        return jsonify(ok=False, error=str(exc)), 503
    except MailDeliveryError as exc:
        return jsonify(ok=False, error=str(exc)), 502
    except Exception:
        from flask import current_app

        current_app.logger.exception('Failed to send OTP')
        return jsonify(ok=False, error='Could not send verification code. Try again later.'), 500

    return jsonify(
        ok=True,
        message='Verification code sent. Check your inbox and spam folder.',
    )


@auth_bp.route('/otp/verify-login', methods=['POST'])
def verify_otp_login():
    data = request.get_json(silent=True) or request.form
    email = (data.get('email') or '').strip().lower()
    code = (data.get('otp') or data.get('code') or '').strip()
    selected_role = (data.get('role') or 'customer').strip()

    if not email or not code:
        return jsonify(ok=False, error='Email and verification code are required.'), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify(ok=False, error='No account found for this email.'), 404
    if user.role != selected_role:
        return jsonify(ok=False, error='Selected role does not match this account.'), 403
    if not verify_otp(email, code):
        return jsonify(ok=False, error='Invalid or expired verification code.'), 400

    _login_user_session(user)
    wants_json = request.is_json or 'application/json' in (request.headers.get('Accept') or '')
    if wants_json:
        target = 'admin.dashboard' if user.role == 'admin' else 'customer.shop_home'
        return jsonify(ok=True, redirect=url_for(target))
    return _redirect_after_login(user)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))
