from flask import Blueprint, render_template, session, redirect, url_for, request
from werkzeug.security import generate_password_hash
from models.models import db, User

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

@user_bp.route('/user/edit-profile', methods=['GET', 'POST'])
def edit_profile():
    email = session.get('user')
    user = User.query.filter_by(email_id=email).first()

    if not user:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        # Check for unique email if changed
        new_email = request.form['email']
        if new_email != user.email_id:
            existing = User.query.filter_by(email_id=new_email).first()
            if existing:
                return "Email already in use.", 400
            user.email_id = new_email
            session['user'] = new_email  # Update session

        # Update other fields
        user.fullname = request.form['fullname']
        user.address = request.form['address']
        user.pincode = request.form['pincode']

        # Optional password change
        new_password = request.form.get('password')
        if new_password:
            user.password = generate_password_hash(new_password)

        db.session.commit()
        return redirect(url_for('user.home'))

    return render_template('user/edit_profile.html', user=user)
