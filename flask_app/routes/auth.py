from flask import Blueprint, render_template, request, redirect, url_for, flash
from ..extensions import db
from ..models import User
from flask_login import login_user, logout_user, login_required, current_user

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('auth.register'))
        user = User(name=name, email=email, role='customer')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        selected_role = request.form.get('role', 'customer')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            if user.role != selected_role:
                flash('Selected role does not match this account.', 'danger')
                return redirect(url_for('auth.login'))
            login_user(user)
            # redirect based on role
            if user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('customer.shop_home'))
        flash('Invalid credentials', 'danger')
        return redirect(url_for('auth.login'))
    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
