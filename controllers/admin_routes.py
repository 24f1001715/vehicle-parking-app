from flask import Blueprint, render_template, session, redirect,url_for, flash, request
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta
from collections import defaultdict
from utils.decorators import admin_required
from models.models import User, ParkingLot, ParkingSpot, Reservation, Admin, db


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
    query = request.args.get('q', '').strip()
    
    if query:
        users = User.query.filter(
            db.or_(
                User.fullname.ilike(f"%{query}%"),
                User.email_id.ilike(f"%{query}%"),
                User.address.ilike(f"%{query}%"),
                User.pincode.ilike(f"%{query}%")
            )
        ).all()
    else:
        users = User.query.all()

    return render_template('admin/users.html', users=users)




@admin_bp.route('/admin/search')
@admin_required
def search():
    filter_by = request.args.get("filter_by")
    query = request.args.get("query")
    results = []

    if filter_by and query:
        q = query.strip()

        if filter_by == "user_email":
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

    
    today = datetime.now().date()
    start_date = today - timedelta(days=6)
    start_date_str = start_date.strftime('%Y-%m-%d')
    trend_labels = [(start_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]

    # Fetch reservations within last 7 days using robust substr comparison for SQLite string dates
    recent_reservations = Reservation.query.filter(
        func.substr(Reservation.parking_timestamp, 1, 10) >= start_date_str
    ).all()

    count_map = {d: 0 for d in trend_labels}
    rev_map = {d: 0.0 for d in trend_labels}

    for r in recent_reservations:
        day_key = str(r.parking_timestamp)[:10]
        if day_key in count_map:
            count_map[day_key] += 1
            if r.total_cost:
                rev_map[day_key] += float(r.total_cost)

    booking_counts = [count_map[day] for day in trend_labels]
    revenues = [round(rev_map[day], 2) for day in trend_labels]

    revenue_per_lot = []
    for lot in lots:
        revenue = db.session.query(db.func.sum(Reservation.total_cost))\
            .filter(Reservation.lot_id == lot.id).scalar()
        revenue_per_lot.append(float(revenue) if revenue else 0.0)

    # All-time metrics across all records
    total_earnings = float(db.session.query(db.func.sum(Reservation.total_cost)).scalar() or 0.0)
    total_bookings = Reservation.query.count()
    top_location = lot_names[revenue_per_lot.index(max(revenue_per_lot))] if (revenue_per_lot and max(revenue_per_lot) > 0) else "N/A"
    available_spots_sum = sum(available_spots)

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
        revenue_per_lot=revenue_per_lot,
        total_earnings=total_earnings,
        total_bookings=total_bookings,
        top_location=top_location,
        available_spots_sum=available_spots_sum
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
                try:
                    lid = int(lot_id)
                except ValueError:
                    continue
                lot = ParkingLot.query.get(lid)
                if lot:
                    # Check if any spots are currently reserved
                    active_count = Reservation.query.filter_by(lot_id=lid, leaving_timestamp=None).count()
                    if active_count > 0:
                        flash(f'Cannot delete lot "{lot.prime_location_name}": active reservations present.', 'warning')
                        continue
                    Reservation.query.filter_by(lot_id=lid).update({'lot_id': None, 'spot_id': None})
                    ParkingSpot.query.filter_by(lot_id=lid).delete()
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
        lot.prime_location_name = request.form['name']
        lot.address = request.form['address']
        lot.pin_code = request.form['pin_code']
        lot.price = float(request.form['price'])
        new_max_spots = int(request.form['max_spots'])

        if new_max_spots != original_max_spots:
            reserved_spots = ParkingSpot.query.filter_by(lot_id=lot.id, status='R').count()
            if reserved_spots > 0:
                error = "Cannot change max spots. Some spots are currently reserved."
                return render_template('admin/edit_lot.html', lot=lot, error=error)

            current_spots = ParkingSpot.query.filter_by(lot_id=lot.id).order_by(ParkingSpot.spot_number).all()
            current_count = len(current_spots)

            if new_max_spots > current_count:
                max_num = max([s.spot_number for s in current_spots], default=0)
                for i in range(1, (new_max_spots - current_count) + 1):
                    db.session.add(ParkingSpot(lot_id=lot.id, spot_number=max_num + i, status='A'))
            elif new_max_spots < current_count:
                spots_to_remove = current_spots[new_max_spots:]
                for s in spots_to_remove:
                    Reservation.query.filter_by(spot_id=s.id).update({'spot_id': None})
                    db.session.delete(s)

            lot.max_spots = new_max_spots

        db.session.commit()
        return redirect(url_for('admin.home'))

    return render_template('admin/edit_lot.html', lot=lot)




@admin_bp.route('/admin/view-lot/<int:lot_id>')
@admin_required
def view_lot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    return render_template('admin/view_lot.html', lot=lot)


@admin_bp.route('/admin/spot/<int:spot_id>/delete', methods=['GET', 'POST'])
@admin_required
def spot_delete(spot_id):
    spot = ParkingSpot.query.get_or_404(spot_id)
    lot = spot.lot  

    if request.method == 'POST':
        if spot.status == 'R':
            flash('Cannot delete spot while it is reserved.', 'danger')
            return redirect(url_for('admin.view_lot', lot_id=spot.lot_id))

        # Detach foreign key references from reservations to prevent IntegrityError
        Reservation.query.filter_by(spot_id=spot.id).update({'spot_id': None})
        db.session.delete(spot)
        
        if lot and lot.max_spots > 0:
            lot.max_spots -= 1
        db.session.commit()
        return redirect(url_for('admin.view_lot', lot_id=lot.id))

    return render_template('admin/view/spot_delete.html', spot=spot)

@admin_bp.route('/admin/lot/<int:lot_id>/add-spot')
@admin_required
def add_spot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)

    max_spot_number = db.session.query(func.max(ParkingSpot.spot_number))\
                        .filter_by(lot_id=lot.id).scalar() or 0

    new_spot = ParkingSpot(lot_id=lot.id, spot_number=max_spot_number + 1)
    db.session.add(new_spot)

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
