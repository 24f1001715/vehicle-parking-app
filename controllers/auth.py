from flask import Blueprint, render_template, request, redirect, url_for, session
from models.models import db, Admin, User
from werkzeug.security import generate_password_hash, check_password_hash
import re

auth_bp = Blueprint('auth', __name__)




@auth_bp.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        admin = Admin.query.filter_by(email_id=email).first()
        user = User.query.filter_by(email_id=email).first()
        if admin and check_password_hash(admin.password, password):
            session['role'] = 'admin'
            session['user'] = email
            return redirect('/admin/dashboard')
        elif user and check_password_hash(user.password, password):
            session['role'] = 'user'
            session['user'] = email
            return redirect('/user/dashboard')
        else:
            return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        fullname = request.form['fullname']
        password = request.form['password']
        address = request.form['address']
        pincode = request.form['pincode']
        if User.query.filter_by(email_id=email).first():
            return render_template('register.html', error='User already exists')
         
        if not is_strong_password(password):
            return render_template('register.html', error='Password must be at least 8 characters long, include a capital letter, a digit, and a special character.')


        hashed_pw = generate_password_hash(password)
        user = User(email_id=email, fullname=fullname, password=hashed_pw, address=address, pincode=pincode)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('auth.login'))
    return render_template('register.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))



def is_strong_password(password):
    return (
        len(password) >= 8 and
        re.search(r"[A-Z]", password) and
        re.search(r"[0-9]", password) and
        re.search(r"[!@#$%^&*()_+{}\[\]:;<>,.?~\\-]", password)
    )
