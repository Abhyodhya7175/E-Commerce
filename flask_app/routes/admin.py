from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user

admin_bp = Blueprint('admin', __name__, template_folder='../templates')


def admin_required(fn):
    from functools import wraps

    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(403)
        return fn(*args, **kwargs)

    return wrapper


@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    return render_template('admin/dashboard.html')
