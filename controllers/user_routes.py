from flask import Blueprint, render_template, session, redirect, url_for

user_bp = Blueprint('user', __name__)

@user_bp.route('/user/dashboard')
def home():
    if session.get('role') != 'user':
        return redirect(url_for('auth.login'))
    return render_template('user/home.html')

@user_bp.route('/user/summary')
def summary():
    if session.get('role') != 'user':
        return redirect(url_for('auth.login'))
    return render_template('user/summary.html')

@user_bp.route('/user/history')
def history():
    if session.get('role') != 'user':
        return redirect(url_for('auth.login'))
    return render_template('user/history.html')

@user_bp.route('/user/edit-profile')
def edit_profile():
    if session.get('role') != 'user':
        return redirect(url_for('auth.login'))
    return render_template('user/edit_profile.html')
