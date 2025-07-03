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
    availability = dict(
        db.session.query(
            ParkingSpot.lot_id,
            func.count().label('available_count')
        ).filter(ParkingSpot.status == 'A')
         .group_by(ParkingSpot.lot_id)
         .all()
    )
    return render_template('admin/home.html', lots=lots, availability=availability)

@admin_bp.route('/admin/users')
@admin_required
def users():
    all_users = User.query.all()
    return render_template('admin/users.html', users=all_users)

from flask import request, render_template
from models.models import Reservation, ParkingLot, ParkingSpot
from sqlalchemy.orm import joinedload

@admin_bp.route('/admin/search')
@admin_required
def search():
    filter_by = request.args.get("filter_by")
    query = request.args.get("query")
    results = []

    if filter_by and query:
        q = query.strip()

        if filter_by == "user_email":
            # You can also search User model directly if needed
            reservations = Reservation.query.filter(Reservation.user_email.ilike(f"%{q}%"))\
                .options(joinedload(Reservation.lot)).all()
            results = [{"type": "reservation", "data": r} for r in reservations]

        elif filter_by == "vehicle_number":
            reservations = Reservation.query.filter(Reservation.vehicle_number.ilike(f"%{q}%"))\
                .options(joinedload(Reservation.lot)).all()
            results = [{"type": "reservation", "data": r} for r in reservations]

        elif filter_by == "lot_name":
            lots = ParkingLot.query.filter(ParkingLot.prime_location_name.ilike(f"%{q}%")).all()
            results = [{"type": "lot", "data": l} for l in lots]

        elif filter_by == "spot_id":
            try:
                spot_id = int(q)
                spots = ParkingSpot.query.options(joinedload(ParkingSpot.lot)).filter_by(id=spot_id).all()

                results = [{"type": "spot", "data": s} for s in spots]
            except ValueError:
                results = []

        elif filter_by == "reservation_id":
            try:
                rid = int(q)
                r = Reservation.query.filter_by(id=rid).options(joinedload(Reservation.lot)).first()
                if r:
                    results = [{"type": "reservation", "data": r}]
            except ValueError:
                results = []

    return render_template('admin/search.html', results=results)


from collections import defaultdict
from datetime import datetime, timedelta
from sqlalchemy import func

@admin_bp.route('/admin/summary')
@admin_required
def summary():
    lots = ParkingLot.query.all()
    lot_ids = [lot.id for lot in lots]
    lot_names = []
    total_spots = []
    available_spots = []
    reserved_spots = []

    for lot in lots:
        lot_names.append(lot.prime_location_name)
        total = len(lot.spots)
        reserved = sum(1 for spot in lot.spots if spot.status == 'R')
        available = total - reserved

        total_spots.append(total)
        reserved_spots.append(reserved)
        available_spots.append(available)

    # --- Booking Trends (last 7 days) ---
    today = datetime.now().date()
    start_date = today - timedelta(days=6)

    reservations = (
        db.session.query(
            func.date(Reservation.parking_timestamp).label('date'),
            func.count().label('count'),
            func.sum(Reservation.total_cost).label('revenue')
        )
        .filter(func.date(Reservation.parking_timestamp) >= start_date)
        .group_by(func.date(Reservation.parking_timestamp))
        .order_by(func.date(Reservation.parking_timestamp))
        .all()
    )

    # Initialize dicts with all dates to show zero even on no-booking days
    trend_labels = [(start_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
    booking_counts = []
    revenues = []

    res_map = {str(row.date): row for row in reservations}
    for day in trend_labels:
        row = res_map.get(day)
        booking_counts.append(row.count if row else 0)
        revenues.append(float(row.revenue) if row and row.revenue else 0)

    # Revenue per lot
    revenue_per_lot = []
    for lot in lots:
        revenue = db.session.query(db.func.sum(Reservation.total_cost))\
            .filter(Reservation.lot_id == lot.id).scalar()
        revenue_per_lot.append(float(revenue) if revenue else 0)


    return render_template(
        'admin/summary.html',
        lot_ids=lot_ids,
        lot_names=lot_names,
        total_spots=total_spots,
        reserved_spots=reserved_spots,
        available_spots=available_spots,
        trend_labels=trend_labels,
        booking_counts=booking_counts,
        revenues=revenues, 
        revenue_per_lot=revenue_per_lot
    )


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
