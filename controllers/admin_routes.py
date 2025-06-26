from flask import Blueprint, render_template, session, redirect, url_for
from utils.decorators import admin_required
from models.models import User, ParkingLot, ParkingSpot, db, Admin, Reservation
from flask import flash
from flask import request
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func

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

@admin_bp.route('/admin/edit-profile', methods=['GET', 'POST'])
@admin_required
def edit_profile():
    email = session.get('user')
    admin = Admin.query.filter_by(email_id=email).first()

    if not admin:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        admin.fullname = request.form['fullname']
        admin.address = request.form['address']
        admin.pincode = request.form['pincode']
        db.session.commit()
        return redirect(url_for('admin.home'))

    return render_template('admin/edit_profile.html', admin=admin)

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


@admin_bp.route('/admin/lot/<int:lot_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_lot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    original_max_spots = lot.max_spots

    if request.method == 'POST':
        # Update basic fields
        lot.prime_location_name = request.form['name']
        lot.address = request.form['address']
        lot.pin_code = request.form['pin_code']
        lot.price = float(request.form['price'])
        new_max_spots = int(request.form['max_spots'])

        # Check if max_spots is changing
        if new_max_spots != original_max_spots:
            # Check for reserved spots
            reserved_spots = ParkingSpot.query.filter_by(lot_id=lot.id, status='R').count()
            if reserved_spots > 0:
                error = "Cannot change max spots. Some spots are currently reserved."
                return render_template('admin/edit_lot.html', lot=lot, error=error)

            # Delete all old spots
            ParkingSpot.query.filter_by(lot_id=lot.id).delete()
            db.session.commit()

            # Update and re-create new spots
            lot.max_spots = new_max_spots
            for i in range(1, new_max_spots + 1):
                spot = ParkingSpot(lot_id=lot.id, spot_number=i)
                db.session.add(spot)

        db.session.commit()
        return redirect(url_for('admin.home'))

    return render_template('admin/edit_lot.html', lot=lot)


#--view lot

@admin_bp.route('/admin/view-lot/<int:lot_id>')
@admin_required
def view_lot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    return render_template('admin/view_lot.html', lot=lot)


@admin_bp.route('/admin/spot/<int:spot_id>/delete', methods=['GET', 'POST'])
def spot_delete(spot_id):
    spot = ParkingSpot.query.get_or_404(spot_id)
    lot = spot.lot  # Access the related ParkingLot

    if request.method == 'POST':
        # Delete the spot
        db.session.delete(spot)
        # Decrement max_spots for that lot
        if lot.max_spots > 0:
            lot.max_spots -= 1
        db.session.commit()
        return redirect(url_for('admin.view_lot', lot_id=lot.id))

    return render_template('admin/view/spot_delete.html', spot=spot)

@admin_bp.route('/admin/lot/<int:lot_id>/add-spot')
@admin_required
def add_spot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)

    # Get the current max spot_number for this lot directly from the database
    max_spot_number = db.session.query(func.max(ParkingSpot.spot_number))\
                        .filter_by(lot_id=lot.id).scalar() or 0

    # Add the new spot
    new_spot = ParkingSpot(lot_id=lot.id, spot_number=max_spot_number + 1)
    db.session.add(new_spot)

    # Update max_spots based on actual count
    total_spots = db.session.query(ParkingSpot).filter_by(lot_id=lot.id).count()
    lot.max_spots = total_spots

    db.session.commit()
    return redirect(url_for('admin.view_lot', lot_id=lot.id))

@admin_bp.route('/admin/spot/<int:spot_id>/details')
@admin_required
def spot_details(spot_id):
    spot = ParkingSpot.query.get_or_404(spot_id)
    reservation = Reservation.query.filter_by(spot_id=spot_id).order_by(Reservation.id.desc()).first()

    if not reservation:
        flash('No reservation found for this spot.', 'warning')
        return redirect(url_for('admin.view_lot', lot_id=spot.lot_id))

    return render_template('admin/view/spot_details.html', spot=spot, reservation=reservation)
