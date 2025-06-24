from flask import Blueprint, render_template, session, redirect, url_for
from models.models import User

user_bp = Blueprint('user', __name__)

@user_bp.route('/user/dashboard')
def user_dashboard():
    if session.get('role') != 'user':
        return redirect(url_for('auth.login'))
    user = User.query.filter_by(email_id=session.get('user')).first()
    return render_template('user_dashboard.html', user=user)
