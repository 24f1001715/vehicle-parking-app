from flask import Blueprint, render_template, session, redirect, url_for
from models.models import User

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin/dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('auth.login'))
    users = User.query.all()
    return render_template('admin_dashboard.html', users=users)
