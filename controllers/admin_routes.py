from flask import Blueprint, render_template, session, redirect, url_for
from utils.decorators import admin_required

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin/dashboard')
@admin_required
def home():
    return render_template('admin/home.html')

@admin_bp.route('/admin/users')
@admin_required
def users():
    return render_template('admin/users.html')

@admin_bp.route('/admin/search')
@admin_required
def search():
    return render_template('admin/search.html')

@admin_bp.route('/admin/summary')
@admin_required
def summary():
    return render_template('admin/summary.html')

@admin_bp.route('/admin/edit-profile')
@admin_required
def edit_profile():
    return render_template('admin/edit_profile.html')
