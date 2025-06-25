from flask import Blueprint, render_template, session, redirect, url_for
from utils.decorators import admin_required
from models.models import User, ParkingLot, ParkingSpot, db
from flask import request
from werkzeug.security import generate_password_hash, check_password_hash

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin/dashboard', methods=['GET', 'POST'])
@admin_required
def home():
    lots = ParkingLot.query.all()
    return render_template('admin/home.html', lots=lots)

@admin_bp.route('/admin/users')
@admin_required
def users():
    all_users = User.query.all()
    return render_template('admin/users.html', users=all_users)

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


@admin_bp.route('/admin/add-lot', methods=['GET', 'POST'])
@admin_required
def add_lot():
    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        pin_code = request.form['pin_code']
        price = request.form['price']
        max_spots = int(request.form['max_spots'])

        new_lot = ParkingLot(
            prime_location_name=name,
            address=address,
            pin_code=pin_code,
            price=float(price),
            max_spots=max_spots
        )
        db.session.add(new_lot)
        db.session.commit()

        for i in range(1, new_lot.max_spots + 1):
            spot = ParkingSpot(lot_id=new_lot.id, spot_number=i)
            db.session.add(spot)
        db.session.commit()

        return redirect(url_for('admin.home'))

    return render_template('admin/add_lot.html')

@admin_bp.route('/admin/delete-lots', methods=['GET', 'POST'])
@admin_required
def delete_parking_lots():
    if request.method == 'POST':
        selected_ids = request.form.getlist('lot_ids')
        if selected_ids:
            for lot_id in selected_ids:
                lot = ParkingLot.query.get(int(lot_id))
                if lot:
                    db.session.delete(lot)
            db.session.commit()
            return redirect(url_for('admin.home'))
    
    lots = ParkingLot.query.all()
    return render_template('admin/delete_lots.html', lots=lots)
