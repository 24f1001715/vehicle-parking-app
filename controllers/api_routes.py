from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import re
import math

from models.models import db, Admin, User, ParkingLot, ParkingSpot, Reservation
from utils.api_decorators import api_admin_required, api_user_required, api_auth_required

api_bp = Blueprint('api', __name__, url_prefix='/api')


def is_strong_password(password):
    return (
        len(password) >= 8 and
        re.search(r"[A-Z]", password) and
        re.search(r"[0-9]", password) and
        re.search(r"[!@#$%^&*()_+{}\[\]:;<>,.?~\\-]", password)
    )


# -----------------------------------------------------------------------------
# AUTH & SESSION ENDPOINTS
# -----------------------------------------------------------------------------

@api_bp.route('/auth/login', methods=['POST'])
def api_login():
    data = request.get_json(silent=True) or request.form.to_dict()
    email = (data.get('email') or '').strip()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password are required'}), 400

    admin = Admin.query.filter_by(email_id=email).first()
    user = User.query.filter_by(email_id=email).first()

    if admin and check_password_hash(admin.password, password):
        session['role'] = 'admin'
        session['user'] = email
        return jsonify({
            'success': True,
            'message': 'Logged in successfully as admin',
            'role': 'admin',
            'user': {
                'id': admin.id,
                'email': admin.email_id,
                'fullname': admin.fullname
            }
        })
    elif user and check_password_hash(user.password, password):
        session['role'] = 'user'
        session['user'] = email
        return jsonify({
            'success': True,
            'message': 'Logged in successfully as user',
            'role': 'user',
            'user': {
                'id': user.id,
                'email': user.email_id,
                'fullname': user.fullname
            }
        })
    else:
        return jsonify({'success': False, 'message': 'Invalid email or password'}), 401


@api_bp.route('/auth/register', methods=['POST'])
def api_register():
    data = request.get_json(silent=True) or request.form.to_dict()
    email = (data.get('email') or '').strip()
    fullname = (data.get('fullname') or '').strip()
    password = data.get('password', '')
    address = (data.get('address') or '').strip()
    pincode = (data.get('pincode') or '').strip()

    if not email or not fullname or not password:
        return jsonify({'success': False, 'message': 'Full name, email, and password are required'}), 400

    if User.query.filter_by(email_id=email).first() or Admin.query.filter_by(email_id=email).first():
        return jsonify({'success': False, 'message': 'User with this email already exists'}), 409

    if not is_strong_password(password):
        return jsonify({
            'success': False,
            'message': 'Password must be at least 8 characters long, include a capital letter, a digit, and a special character.'
        }), 400

    hashed_pw = generate_password_hash(password)
    user = User(
        email_id=email,
        fullname=fullname,
        password=hashed_pw,
        address=address,
        pincode=pincode
    )
    db.session.add(user)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Registration successful',
        'user': {
            'id': user.id,
            'email': user.email_id,
            'fullname': user.fullname
        }
    }), 201


@api_bp.route('/auth/logout', methods=['POST', 'GET'])
def api_logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})


@api_bp.route('/auth/me', methods=['GET'])
def api_current_user():
    role = session.get('role')
    email = session.get('user')

    if not role or not email:
        return jsonify({'authenticated': False}), 200

    if role == 'admin':
        admin = Admin.query.filter_by(email_id=email).first()
        if not admin:
            session.clear()
            return jsonify({'authenticated': False}), 200
        return jsonify({
            'authenticated': True,
            'role': 'admin',
            'user': {
                'id': admin.id,
                'email': admin.email_id,
                'fullname': admin.fullname,
                'address': admin.address,
                'pincode': admin.pincode
            }
        })
    elif role == 'user':
        user = User.query.filter_by(email_id=email).first()
        if not user:
            session.clear()
            return jsonify({'authenticated': False}), 200
        return jsonify({
            'authenticated': True,
            'role': 'user',
            'user': {
                'id': user.id,
                'email': user.email_id,
                'fullname': user.fullname,
                'address': user.address,
                'pincode': user.pincode
            }
        })

    return jsonify({'authenticated': False}), 200


# -----------------------------------------------------------------------------
# PARKING LOTS & SPOTS ENDPOINTS
# -----------------------------------------------------------------------------

@api_bp.route('/lots', methods=['GET'])
@api_auth_required
def api_get_lots():
    query = request.args.get('q', '').strip()
    lots_query = ParkingLot.query

    if query:
        search_pattern = f"%{query}%"
        lots_query = lots_query.filter(
            db.or_(
                ParkingLot.prime_location_name.ilike(search_pattern),
                ParkingLot.address.ilike(search_pattern),
                ParkingLot.pin_code.ilike(search_pattern)
            )
        )

    lots = lots_query.all()
    results = []
    for lot in lots:
        available_count = ParkingSpot.query.filter_by(lot_id=lot.id, status='A').count()
        reserved_count = ParkingSpot.query.filter_by(lot_id=lot.id, status='R').count()
        results.append({
            'id': lot.id,
            'name': lot.prime_location_name,
            'address': lot.address or '',
            'pin_code': lot.pin_code or '',
            'price': lot.price,
            'max_spots': lot.max_spots,
            'available_spots': available_count,
            'reserved_spots': reserved_count
        })

    return jsonify({'success': True, 'lots': results})


@api_bp.route('/lots/<int:lot_id>', methods=['GET'])
@api_auth_required
def api_get_lot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    available_count = ParkingSpot.query.filter_by(lot_id=lot.id, status='A').count()
    spots = [
        {
            'id': s.id,
            'spot_number': s.spot_number,
            'status': s.status,
            'is_available': s.status == 'A'
        }
        for s in sorted(lot.spots, key=lambda x: x.spot_number)
    ]

    return jsonify({
        'success': True,
        'lot': {
            'id': lot.id,
            'name': lot.prime_location_name,
            'address': lot.address,
            'pin_code': lot.pin_code,
            'price': lot.price,
            'max_spots': lot.max_spots,
            'available_spots': available_count,
            'spots': spots
        }
    })


@api_bp.route('/lots', methods=['POST'])
@api_admin_required
def api_create_lot():
    data = request.get_json(silent=True) or request.form.to_dict()
    name = (data.get('name') or '').strip()
    address = (data.get('address') or '').strip()
    pin_code = (data.get('pin_code') or '').strip()
    price = data.get('price')
    max_spots = data.get('max_spots')

    if not name or price is None or max_spots is None:
        return jsonify({'success': False, 'message': 'Name, price, and max_spots are required'}), 400

    try:
        price = float(price)
        max_spots = int(max_spots)
        if max_spots <= 0 or price < 0:
            raise ValueError()
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Valid positive numbers required for max spots and price'}), 400

    new_lot = ParkingLot(
        prime_location_name=name,
        address=address,
        pin_code=pin_code,
        price=price,
        max_spots=max_spots
    )
    db.session.add(new_lot)
    db.session.commit()

    # Generate initial spots
    for i in range(1, max_spots + 1):
        spot = ParkingSpot(lot_id=new_lot.id, spot_number=i, status='A')
        db.session.add(spot)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Parking lot created successfully',
        'lot_id': new_lot.id
    }), 201


@api_bp.route('/lots/<int:lot_id>', methods=['PUT', 'PATCH'])
@api_admin_required
def api_update_lot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    data = request.get_json(silent=True) or request.form.to_dict()

    name = data.get('name')
    address = data.get('address')
    pin_code = data.get('pin_code')
    price = data.get('price')
    new_max_spots = data.get('max_spots')

    if name:
        lot.prime_location_name = name.strip()
    if address is not None:
        lot.address = address.strip()
    if pin_code is not None:
        lot.pin_code = pin_code.strip()
    if price is not None:
        try:
            lot.price = float(price)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'Invalid price value'}), 400

    if new_max_spots is not None:
        try:
            new_max_spots = int(new_max_spots)
            if new_max_spots <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'Invalid max_spots value'}), 400

        if new_max_spots != lot.max_spots:
            # Check if any spots are currently reserved
            reserved_count = ParkingSpot.query.filter_by(lot_id=lot.id, status='R').count()
            if reserved_count > 0:
                return jsonify({
                    'success': False,
                    'message': f'Cannot resize lot while {reserved_count} spots are actively reserved.'
                }), 409

            # Safe spot adjustment: expand or trim available spots without breaking foreign keys
            current_spots = ParkingSpot.query.filter_by(lot_id=lot.id).order_by(ParkingSpot.spot_number).all()
            current_count = len(current_spots)

            if new_max_spots > current_count:
                max_num = max([s.spot_number for s in current_spots], default=0)
                for i in range(1, (new_max_spots - current_count) + 1):
                    db.session.add(ParkingSpot(lot_id=lot.id, spot_number=max_num + i, status='A'))
            elif new_max_spots < current_count:
                # Remove from the highest spot numbers down to new_max_spots
                spots_to_remove = current_spots[new_max_spots:]
                for s in spots_to_remove:
                    # Clean up orphaned reservation reference if any
                    Reservation.query.filter_by(spot_id=s.id).update({'spot_id': None})
                    db.session.delete(s)

            lot.max_spots = new_max_spots

    db.session.commit()
    return jsonify({'success': True, 'message': 'Parking lot updated successfully'})


@api_bp.route('/lots/<int:lot_id>', methods=['DELETE'])
@api_admin_required
def api_delete_lot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)

    # Check for active reservations
    active_reservations = Reservation.query.filter_by(lot_id=lot_id, leaving_timestamp=None).count()
    if active_reservations > 0:
        return jsonify({
            'success': False,
            'message': f'Cannot delete parking lot: {active_reservations} spot(s) are currently in active use.'
        }), 409

    # Clean historical reservations referencing this lot
    Reservation.query.filter_by(lot_id=lot_id).update({'lot_id': None, 'spot_id': None})
    ParkingSpot.query.filter_by(lot_id=lot_id).delete()
    db.session.delete(lot)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Parking lot deleted successfully'})


@api_bp.route('/lots/bulk-delete', methods=['POST'])
@api_admin_required
def api_bulk_delete_lots():
    data = request.get_json(silent=True) or request.form.to_dict()
    lot_ids = data.get('lot_ids') or []

    if not isinstance(lot_ids, list) or not lot_ids:
        return jsonify({'success': False, 'message': 'List of lot_ids is required'}), 400

    deleted_count = 0
    blocked_count = 0

    for lid in lot_ids:
        try:
            lid = int(lid)
        except (ValueError, TypeError):
            continue

        lot = ParkingLot.query.get(lid)
        if not lot:
            continue

        active = Reservation.query.filter_by(lot_id=lid, leaving_timestamp=None).count()
        if active > 0:
            blocked_count += 1
            continue

        Reservation.query.filter_by(lot_id=lid).update({'lot_id': None, 'spot_id': None})
        ParkingSpot.query.filter_by(lot_id=lid).delete()
        db.session.delete(lot)
        deleted_count += 1

    db.session.commit()
    return jsonify({
        'success': True,
        'deleted_count': deleted_count,
        'blocked_due_to_active_booking': blocked_count,
        'message': f'Deleted {deleted_count} lot(s).' + (f' ({blocked_count} skipped due to active bookings)' if blocked_count else '')
    })


@api_bp.route('/lots/<int:lot_id>/spots', methods=['POST'])
@api_admin_required
def api_add_spot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    max_spot_number = db.session.query(db.func.max(ParkingSpot.spot_number))\
                        .filter_by(lot_id=lot.id).scalar() or 0

    new_spot = ParkingSpot(lot_id=lot.id, spot_number=max_spot_number + 1, status='A')
    db.session.add(new_spot)
    lot.max_spots = ParkingSpot.query.filter_by(lot_id=lot.id).count() + 1
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Spot added successfully',
        'spot': {
            'id': new_spot.id,
            'spot_number': new_spot.spot_number,
            'status': new_spot.status
        }
    }), 201


@api_bp.route('/spots/<int:spot_id>', methods=['DELETE'])
@api_admin_required
def api_delete_spot(spot_id):
    spot = ParkingSpot.query.get_or_404(spot_id)

    if spot.status == 'R':
        return jsonify({'success': False, 'message': 'Cannot delete spot while actively reserved.'}), 409

    lot = spot.lot
    Reservation.query.filter_by(spot_id=spot_id).update({'spot_id': None})
    db.session.delete(spot)

    if lot and lot.max_spots > 0:
        lot.max_spots -= 1

    db.session.commit()
    return jsonify({'success': True, 'message': 'Spot deleted successfully'})


@api_bp.route('/spots/<int:spot_id>/details', methods=['GET'])
@api_admin_required
def api_spot_details(spot_id):
    spot = ParkingSpot.query.get_or_404(spot_id)
    reservation = Reservation.query.filter_by(spot_id=spot_id).order_by(Reservation.id.desc()).first()

    res_data = None
    if reservation:
        res_data = {
            'reservation_id': reservation.id,
            'user_email': reservation.user_email,
            'vehicle_number': reservation.vehicle_number,
            'parking_timestamp': reservation.parking_timestamp,
            'leaving_timestamp': reservation.leaving_timestamp,
            'cost_per_hour': reservation.cost_per_hour,
            'total_cost': reservation.total_cost
        }

    return jsonify({
        'success': True,
        'spot': {
            'id': spot.id,
            'spot_number': spot.spot_number,
            'status': spot.status,
            'lot_id': spot.lot_id,
            'lot_name': spot.lot.prime_location_name if spot.lot else 'Unknown'
        },
        'latest_reservation': res_data
    })


# -----------------------------------------------------------------------------
# RESERVATIONS / BOOKINGS ENDPOINTS
# -----------------------------------------------------------------------------

@api_bp.route('/bookings', methods=['GET'])
@api_user_required
def api_get_user_bookings():
    email = session.get('user')
    filter_option = request.args.get('filter', 'all')

    reservations = (
        Reservation.query
        .filter_by(user_email=email)
        .order_by(Reservation.id.desc())
        .all()
    )

    now = datetime.now()
    results = []

    for res in reservations:
        is_released = res.leaving_timestamp is not None

        if filter_option == 'released' and not is_released:
            continue
        if filter_option == 'not_released' and is_released:
            continue

        try:
            start_time = datetime.strptime(res.parking_timestamp, "%Y-%m-%d %H:%M:%S")
        except Exception:
            start_time = now

        if res.leaving_timestamp:
            try:
                end_time = datetime.strptime(res.leaving_timestamp, "%Y-%m-%d %H:%M:%S")
            except Exception:
                end_time = now
        else:
            end_time = now

        duration_hours = max(math.ceil((end_time - start_time).total_seconds() / 3600), 1)
        price = res.cost_per_hour or (res.lot.price if res.lot else 0)
        estimated_total = round(duration_hours * price, 2)

        results.append({
            'id': res.id,
            'lot_id': res.lot_id,
            'lot_name': res.lot.prime_location_name if res.lot else 'N/A',
            'address': res.lot.address if res.lot else 'N/A',
            'pincode': res.lot.pin_code if res.lot else 'N/A',
            'spot_id': res.spot_id,
            'spot_number': res.spot.spot_number if res.spot else None,
            'vehicle_number': res.vehicle_number,
            'parking_timestamp': res.parking_timestamp,
            'leaving_timestamp': res.leaving_timestamp,
            'price_per_hr': price,
            'duration_hours': duration_hours,
            'total_cost': res.total_cost if res.total_cost is not None else estimated_total,
            'released': is_released
        })

    return jsonify({'success': True, 'bookings': results})


@api_bp.route('/bookings', methods=['POST'])
@api_user_required
def api_create_booking():
    user_email = session.get('user')
    data = request.get_json(silent=True) or request.form.to_dict()

    lot_id = data.get('lot_id')
    vehicle_number = (data.get('vehicle_number') or '').strip()

    if not lot_id or not vehicle_number:
        return jsonify({'success': False, 'message': 'lot_id and vehicle_number are required'}), 400

    try:
        lot_id = int(lot_id)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Invalid lot_id'}), 400

    lot = ParkingLot.query.get(lot_id)
    if not lot:
        return jsonify({'success': False, 'message': 'Parking lot not found'}), 404

    # Atomic allocation of first available spot
    available_spot = ParkingSpot.query.filter_by(lot_id=lot_id, status='A').order_by(ParkingSpot.spot_number).first()
    if not available_spot:
        return jsonify({'success': False, 'message': 'No available parking spots in this lot'}), 409

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    reservation = Reservation(
        spot_id=available_spot.id,
        lot_id=lot.id,
        user_email=user_email,
        parking_timestamp=now_str,
        leaving_timestamp=None,
        cost_per_hour=lot.price,
        total_cost=None,
        vehicle_number=vehicle_number
    )

    available_spot.status = 'R'
    db.session.add(reservation)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Parking spot booked successfully',
        'reservation': {
            'id': reservation.id,
            'lot_id': lot.id,
            'lot_name': lot.prime_location_name,
            'spot_id': available_spot.id,
            'spot_number': available_spot.spot_number,
            'vehicle_number': vehicle_number,
            'parking_timestamp': now_str,
            'cost_per_hour': lot.price
        }
    }), 201


@api_bp.route('/bookings/<int:reservation_id>/release', methods=['POST'])
@api_user_required
def api_release_booking(reservation_id):
    reservation = Reservation.query.get_or_404(reservation_id)
    user_email = session.get('user')

    if reservation.user_email != user_email:
        return jsonify({'success': False, 'message': 'You do not have permission to release this booking.'}), 403

    if reservation.leaving_timestamp:
        return jsonify({'success': False, 'message': 'Spot has already been released.', 'total_cost': reservation.total_cost}), 400

    now = datetime.now()
    try:
        start = datetime.strptime(reservation.parking_timestamp, "%Y-%m-%d %H:%M:%S")
    except Exception:
        start = now

    hours = max(math.ceil((now - start).total_seconds() / 3600), 1)
    rate = reservation.cost_per_hour or (reservation.lot.price if reservation.lot else 0)
    total_cost = round(hours * rate, 2)

    reservation.leaving_timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    reservation.total_cost = total_cost

    if reservation.spot:
        reservation.spot.status = 'A'

    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Spot released successfully',
        'total_cost': total_cost,
        'duration_hours': hours,
        'leaving_timestamp': reservation.leaving_timestamp
    })


# -----------------------------------------------------------------------------
# ADMIN SEARCH & METRICS ENDPOINTS
# -----------------------------------------------------------------------------

@api_bp.route('/admin/users', methods=['GET'])
@api_admin_required
def api_get_users():
    query = request.args.get('q', '').strip()
    users_query = User.query

    if query:
        pattern = f"%{query}%"
        users_query = users_query.filter(
            db.or_(
                User.fullname.ilike(pattern),
                User.email_id.ilike(pattern),
                User.address.ilike(pattern),
                User.pincode.ilike(pattern)
            )
        )

    users = users_query.all()
    results = [
        {
            'id': u.id,
            'email': u.email_id,
            'fullname': u.fullname,
            'address': u.address or '',
            'pincode': u.pincode or ''
        }
        for u in users
    ]
    return jsonify({'success': True, 'users': results})


@api_bp.route('/admin/search', methods=['GET'])
@api_admin_required
def api_search():
    filter_by = request.args.get('filter_by')
    query = request.args.get('query', '').strip()

    if not filter_by or not query:
        return jsonify({'success': True, 'results': []})

    results = []
    if filter_by == 'user_email':
        reservations = Reservation.query.filter(Reservation.user_email.ilike(f"%{query}%")).all()
        for r in reservations:
            results.append({
                'type': 'reservation',
                'id': r.id,
                'user_email': r.user_email,
                'vehicle_number': r.vehicle_number,
                'lot_name': r.lot.prime_location_name if r.lot else 'N/A',
                'spot_id': r.spot_id,
                'parking_timestamp': r.parking_timestamp,
                'leaving_timestamp': r.leaving_timestamp,
                'total_cost': r.total_cost,
                'status': 'Completed' if r.leaving_timestamp else 'Active'
            })

    elif filter_by == 'vehicle_number':
        reservations = Reservation.query.filter(Reservation.vehicle_number.ilike(f"%{query}%")).all()
        for r in reservations:
            results.append({
                'type': 'reservation',
                'id': r.id,
                'user_email': r.user_email,
                'vehicle_number': r.vehicle_number,
                'lot_name': r.lot.prime_location_name if r.lot else 'N/A',
                'spot_id': r.spot_id,
                'parking_timestamp': r.parking_timestamp,
                'leaving_timestamp': r.leaving_timestamp,
                'total_cost': r.total_cost,
                'status': 'Completed' if r.leaving_timestamp else 'Active'
            })

    elif filter_by == 'lot_name':
        lots = ParkingLot.query.filter(ParkingLot.prime_location_name.ilike(f"%{query}%")).all()
        for l in lots:
            results.append({
                'type': 'lot',
                'id': l.id,
                'name': l.prime_location_name,
                'address': l.address,
                'pin_code': l.pin_code,
                'price': l.price,
                'max_spots': l.max_spots
            })

    elif filter_by == 'spot_id':
        try:
            spot_id = int(query)
            spots = ParkingSpot.query.filter_by(id=spot_id).all()
            for s in spots:
                results.append({
                    'type': 'spot',
                    'id': s.id,
                    'spot_number': s.spot_number,
                    'status': s.status,
                    'lot_name': s.lot.prime_location_name if s.lot else 'N/A'
                })
        except ValueError:
            pass

    elif filter_by == 'reservation_id':
        try:
            rid = int(query)
            r = Reservation.query.get(rid)
            if r:
                results.append({
                    'type': 'reservation',
                    'id': r.id,
                    'user_email': r.user_email,
                    'vehicle_number': r.vehicle_number,
                    'lot_name': r.lot.prime_location_name if r.lot else 'N/A',
                    'spot_id': r.spot_id,
                    'parking_timestamp': r.parking_timestamp,
                    'leaving_timestamp': r.leaving_timestamp,
                    'total_cost': r.total_cost,
                    'status': 'Completed' if r.leaving_timestamp else 'Active'
                })
        except ValueError:
            pass

    return jsonify({'success': True, 'results': results})


@api_bp.route('/admin/summary', methods=['GET'])
@api_admin_required
def api_admin_summary():
    from datetime import timedelta
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
    trend_labels = [(start_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]

    # Query reservations within last 7 days
    recent_reservations = Reservation.query.filter(
        db.func.substr(Reservation.parking_timestamp, 1, 10) >= start_date.strftime('%Y-%m-%d')
    ).all()

    count_map = {d: 0 for d in trend_labels}
    rev_map = {d: 0.0 for d in trend_labels}

    for r in recent_reservations:
        day_key = str(r.parking_timestamp)[:10]
        if day_key in count_map:
            count_map[day_key] += 1
            if r.total_cost:
                rev_map[day_key] += float(r.total_cost)

    booking_counts = [count_map[d] for d in trend_labels]
    revenues = [round(rev_map[d], 2) for d in trend_labels]

    revenue_per_lot = []
    for lot in lots:
        total_lot_rev = db.session.query(db.func.sum(Reservation.total_cost))\
            .filter(Reservation.lot_id == lot.id).scalar() or 0.0
        revenue_per_lot.append(float(total_lot_rev))

    # All-time total earnings from all completed reservations
    total_earnings = db.session.query(db.func.sum(Reservation.total_cost)).scalar() or 0.0
    total_bookings = Reservation.query.count()
    top_location = lot_names[revenue_per_lot.index(max(revenue_per_lot))] if (revenue_per_lot and max(revenue_per_lot) > 0) else "N/A"

    return jsonify({
        'success': True,
        'summary': {
            'total_earnings': round(float(total_earnings), 2),
            'total_bookings': total_bookings,
            'available_spots_sum': sum(available_spots),
            'top_location': top_location,
            'lot_ids': lot_ids,
            'lot_names': lot_names,
            'total_spots': total_spots,
            'available_spots': available_spots,
            'reserved_spots': reserved_spots,
            'trend_labels': trend_labels,
            'booking_counts': booking_counts,
            'revenues': revenues,
            'revenue_per_lot': revenue_per_lot
        }
    })


@api_bp.route('/user/summary', methods=['GET'])
@api_user_required
def api_user_summary():
    from datetime import timedelta
    user_email = session.get('user')
    reservations = Reservation.query.filter_by(user_email=user_email).all()

    today = datetime.now().date()
    start_date = today - timedelta(days=6)
    trend_labels = [(start_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]

    count_map = {d: 0 for d in trend_labels}
    cost_map = {d: 0.0 for d in trend_labels}
    lot_count = {}
    reserved_count = 0
    completed_count = 0
    total_spent = 0.0
    last_booking_date = None

    for r in reservations:
        try:
            p_dt = datetime.strptime(r.parking_timestamp, '%Y-%m-%d %H:%M:%S')
            d_key = p_dt.date().strftime('%Y-%m-%d')
            if d_key in count_map:
                count_map[d_key] += 1
                if r.total_cost:
                    cost_map[d_key] += float(r.total_cost)
        except Exception:
            pass

        if r.total_cost:
            total_spent += float(r.total_cost)

        if r.leaving_timestamp:
            completed_count += 1
        else:
            reserved_count += 1

        if r.lot:
            lot_count[r.lot.prime_location_name] = lot_count.get(r.lot.prime_location_name, 0) + 1

        try:
            p_dt = datetime.strptime(r.parking_timestamp, '%Y-%m-%d %H:%M:%S')
            if not last_booking_date or p_dt > last_booking_date:
                last_booking_date = p_dt
        except Exception:
            pass

    return jsonify({
        'success': True,
        'summary': {
            'total_bookings': len(reservations),
            'total_spent': round(total_spent, 2),
            'active_bookings': reserved_count,
            'completed_bookings': completed_count,
            'last_booking_date': last_booking_date.strftime('%Y-%m-%d') if last_booking_date else "N/A",
            'trend_labels': trend_labels,
            'booking_counts': [count_map[d] for d in trend_labels],
            'costs': [round(cost_map[d], 2) for d in trend_labels],
            'lot_names': list(lot_count.keys()),
            'lot_usage': list(lot_count.values())
        }
    })


# -----------------------------------------------------------------------------
# PROFILE MANAGEMENT ENDPOINTS
# -----------------------------------------------------------------------------

@api_bp.route('/profile', methods=['GET'])
@api_auth_required
def api_get_profile():
    role = session.get('role')
    email = session.get('user')

    if role == 'admin':
        admin = Admin.query.filter_by(email_id=email).first()
        return jsonify({
            'success': True,
            'role': 'admin',
            'profile': {
                'fullname': admin.fullname,
                'email': admin.email_id,
                'address': admin.address,
                'pincode': admin.pincode
            }
        })
    else:
        user = User.query.filter_by(email_id=email).first()
        return jsonify({
            'success': True,
            'role': 'user',
            'profile': {
                'fullname': user.fullname,
                'email': user.email_id,
                'address': user.address,
                'pincode': user.pincode
            }
        })


@api_bp.route('/profile', methods=['PUT'])
@api_auth_required
def api_update_profile():
    role = session.get('role')
    email = session.get('user')
    data = request.get_json(silent=True) or request.form.to_dict()

    if role == 'admin':
        admin = Admin.query.filter_by(email_id=email).first()
        if not admin:
            return jsonify({'success': False, 'message': 'Admin not found'}), 404

        if data.get('fullname'):
            admin.fullname = data['fullname'].strip()
        if 'address' in data:
            admin.address = data['address'].strip()
        if 'pincode' in data:
            admin.pincode = data['pincode'].strip()
        db.session.commit()
        return jsonify({'success': True, 'message': 'Admin profile updated successfully'})

    else:
        user = User.query.filter_by(email_id=email).first()
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404

        new_email = (data.get('email') or '').strip()
        if new_email and new_email != user.email_id:
            if User.query.filter_by(email_id=new_email).first() or Admin.query.filter_by(email_id=new_email).first():
                return jsonify({'success': False, 'message': 'Email already registered to another account'}), 400
            Reservation.query.filter_by(user_email=user.email_id).update({'user_email': new_email})
            user.email_id = new_email
            session['user'] = new_email

        if data.get('fullname'):
            user.fullname = data['fullname'].strip()
        if 'address' in data:
            user.address = data['address'].strip()
        if 'pincode' in data:
            user.pincode = data['pincode'].strip()

        new_pw = data.get('password')
        if new_pw:
            if not is_strong_password(new_pw):
                return jsonify({
                    'success': False,
                    'message': 'Password must be at least 8 characters long, include a capital letter, a digit, and a special character.'
                }), 400
            user.password = generate_password_hash(new_pw)

        db.session.commit()
        return jsonify({'success': True, 'message': 'Profile updated successfully'})
