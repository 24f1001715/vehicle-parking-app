# routes/user.py

from flask import Blueprint, render_template, session, redirect, url_for, request
from werkzeug.security import generate_password_hash
from models.models import db, User, ParkingLot, ParkingSpot, Reservation
from flask import flash
from utils.decorators import user_required
from sqlalchemy import func

user_bp = Blueprint('user', __name__)

from datetime import datetime
from sqlalchemy.orm import joinedload

from datetime import datetime

@user_bp.route('/user/dashboard')
@user_required
def home():
    email = session.get('user')

    reservations = (
        Reservation.query
        .filter_by(user_email=email)
        .options(
            joinedload(Reservation.spot),
            joinedload(Reservation.lot)
        )
        .order_by(Reservation.parking_timestamp.desc())
        .all()
    )

    now = datetime.now()
    booking_data = []

    for res in reservations:
        # Skip if lot or spot is missing (in case of deletion)
        if not res.lot:
            continue

        start_time = datetime.strptime(res.parking_timestamp, "%Y-%m-%d %H:%M:%S")
        if res.leaving_timestamp:
            end_time = datetime.strptime(res.leaving_timestamp, "%Y-%m-%d %H:%M:%S")
        else:
            end_time = now

        duration_hours = max((end_time - start_time).total_seconds() / 3600, 1)
        price = res.cost_per_hour or res.lot.price or 0
        total = round(duration_hours * price, 2)

        booking_data.append({
            'id': res.id,
            'lot_name': res.lot.prime_location_name or 'Unknown',
            'address': res.lot.address or 'N/A',
            'pincode': res.lot.pin_code or 'N/A',
            'price_per_hr': price,
            'booked_at': start_time.strftime("%Y-%m-%d %H:%M"),
            'released': res.leaving_timestamp is not None,
            'total_cost': res.total_cost or total,
        })

    return render_template("user/home.html", bookings=booking_data)


@user_bp.route('/user/summary')
@user_required
def summary():
    return render_template('user/summary.html')



@user_bp.route('/user/book')
@user_required
def book():
    lots = ParkingLot.query.all()

    availability = dict(
        db.session.query(
            ParkingSpot.lot_id,
            func.count().label('available_count')
        ).filter(ParkingSpot.status == 'A')
         .group_by(ParkingSpot.lot_id)
         .all()
    )

    return render_template('user/book.html', lots=lots, availability=availability)



@user_bp.route('/user/edit-profile', methods=['GET', 'POST'])
@user_required
def edit_profile():
    email = session.get('user')
    user = User.query.filter_by(email_id=email).first()

    if not user:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        new_email = request.form['email']
        if new_email != user.email_id:
            if User.query.filter_by(email_id=new_email).first():
                return "Email already in use.", 400
            user.email_id = new_email
            session['user'] = new_email

        user.fullname = request.form['fullname']
        user.address = request.form['address']
        user.pincode = request.form['pincode']

        new_password = request.form.get('password')
        if new_password:
            user.password = generate_password_hash(new_password)

        db.session.commit()
        return redirect(url_for('user.home'))

    return render_template('user/edit_profile.html', user=user)


@user_bp.route('/confirm-booking/<int:lot_id>', methods=['GET', 'POST'])
@user_required
def confirm_booking(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    user_email = session.get('user')  # fixed to use 'user'

    # Get the first available spot
    available_spot = ParkingSpot.query.filter_by(lot_id=lot_id, status='A').first()
    if not available_spot:
        flash('No available spots in this lot.', 'error')
        return redirect(url_for('user.book'))

    if request.method == 'POST':
        vehicle_number = request.form['vehicle_number']
        
        from datetime import datetime
        now = datetime.now()

        reservation = Reservation(
            spot_id=available_spot.id,
            lot_id=lot_id,
            user_email=user_email,
            parking_timestamp=now.strftime("%Y-%m-%d %H:%M:%S"),
            leaving_timestamp=None,
            cost_per_hour=lot.price,
            total_cost=None,
            vehicle_number=vehicle_number
        )

        # Mark spot as reserved
        available_spot.status = 'R'

        db.session.add(reservation)
        db.session.commit()

        flash('Booking confirmed!', 'success')
        return redirect(url_for('user.book'))

    return render_template('user/confirm_booking.html', lot=lot, spot=available_spot, user_email=user_email)

from datetime import datetime

@user_bp.route('/release/<int:reservation_id>', endpoint='release_spot')
@user_required
def release_spot_page(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)

    if reservation.leaving_timestamp:
        flash('This spot has already been released.', 'info')
        return redirect(url_for('user.home'))

    start = datetime.strptime(reservation.parking_timestamp, "%Y-%m-%d %H:%M:%S")
    now = datetime.now()
    duration_hrs = max((now - start).total_seconds() / 3600, 1)
    estimated_cost = round(duration_hrs * reservation.cost_per_hour, 2)

    return render_template('user/release_confirm.html', reservation=reservation,
                           start=start.strftime("%Y-%m-%d %H:%M"),
                           now=now.strftime("%Y-%m-%d %H:%M"),
                           duration=round(duration_hrs, 2),
                           estimated_cost=estimated_cost)

@user_bp.route('/user/release-confirm/<int:reservation_id>', methods=['POST'])
@user_required
def release_spot_confirm(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)

    if reservation.leaving_timestamp:
        flash('Already released.', 'info')
        return redirect(url_for('user.home'))

    now = datetime.now()
    start = datetime.strptime(reservation.parking_timestamp, "%Y-%m-%d %H:%M:%S")
    hours = max((now - start).total_seconds() / 3600, 1)

    reservation.leaving_timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    reservation.total_cost = round(hours * reservation.cost_per_hour, 2)

    # Free up spot
    reservation.spot.status = 'A'

    db.session.commit()
    flash('Spot released successfully!', 'success')
    return redirect(url_for('user.home'))

