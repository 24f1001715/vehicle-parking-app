from flask import Blueprint, request
from flask_restful import Api, Resource, abort
from models.models import db, ParkingLot, ParkingSpot, Reservation
from datetime import datetime

api_restful_bp = Blueprint('api_restful', __name__)
api = Api(api_restful_bp)

# --------- Parking Lot Resources ---------
class LotList(Resource):
    def get(self):
        lots = ParkingLot.query.all()
        return [{
            'id': lot.id,
            'name': lot.prime_location_name,
            'address': lot.address,
            'pin_code': lot.pin_code,
            'price': lot.price,
            'max_spots': lot.max_spots
        } for lot in lots]

    def post(self):
        data = request.get_json()
        if not data or 'name' not in data:
            abort(400, message='Missing required field: name')

        lot = ParkingLot(
            prime_location_name=data['name'],
            address=data.get('address', ''),
            pin_code=data.get('pin_code', ''),
            price=float(data.get('price', 0)),
            max_spots=int(data.get('max_spots', 0))
        )
        db.session.add(lot)
        db.session.commit()

        # Auto-create spots
        for i in range(1, lot.max_spots + 1):
            db.session.add(ParkingSpot(lot_id=lot.id, spot_number=i))
        db.session.commit()

        return {'message': 'Lot created', 'id': lot.id}, 201

class Lot(Resource):
    def get(self, lot_id):
        lot = ParkingLot.query.get_or_404(lot_id)
        return {
            'id': lot.id,
            'name': lot.prime_location_name,
            'address': lot.address,
            'pin_code': lot.pin_code,
            'price': lot.price,
            'max_spots': lot.max_spots
        }

# --------- Spot Resources ---------
class SpotList(Resource):
    def get(self, lot_id):
        spots = ParkingSpot.query.filter_by(lot_id=lot_id).all()
        return [{
            'id': spot.id,
            'spot_number': spot.spot_number,
            'status': spot.status
        } for spot in spots]

class Spot(Resource):
    def get(self, spot_id):
        spot = ParkingSpot.query.get_or_404(spot_id)
        return {
            'id': spot.id,
            'lot_id': spot.lot_id,
            'spot_number': spot.spot_number,
            'status': spot.status
        }

# --------- Reservation Resources ---------
class ReservationList(Resource):
    def get(self):
        reservations = Reservation.query.all()
        return [{
            'id': r.id,
            'user_email': r.user_email,
            'vehicle_number': r.vehicle_number,
            'timestamp': r.parking_timestamp.isoformat(),
            'total_cost': r.total_cost,
            'lot_id': r.lot_id,
            'spot_id': r.spot_id
        } for r in reservations]

    def post(self):
        data = request.get_json()
        if not data or not all(k in data for k in ('user_email', 'vehicle_number', 'total_cost', 'lot_id', 'spot_id')):
            abort(400, message='Missing required fields')

        # Check spot availability
        spot = ParkingSpot.query.get(data['spot_id'])
        if not spot or spot.status == 'R':
            abort(400, message='Spot not available or does not exist')

        reservation = Reservation(
            user_email=data['user_email'],
            vehicle_number=data['vehicle_number'],
            parking_timestamp=datetime.now(),
            total_cost=float(data['total_cost']),
            lot_id=data['lot_id'],
            spot_id=data['spot_id']
        )

        spot.status = 'R'  # mark as reserved
        db.session.add(reservation)
        db.session.commit()

        return {'message': 'Reservation successful', 'id': reservation.id}, 201

class Reservation(Resource):
    def get(self, reservation_id):
        r = Reservation.query.get_or_404(reservation_id)
        return {
            'id': r.id,
            'user_email': r.user_email,
            'vehicle_number': r.vehicle_number,
            'timestamp': r.parking_timestamp.isoformat(),
            'total_cost': r.total_cost,
            'lot_id': r.lot_id,
            'spot_id': r.spot_id
        }

# --------- Route Registration ---------
api.add_resource(LotList, '/api/lots')
api.add_resource(Lot, '/api/lots/<int:lot_id>')
api.add_resource(SpotList, '/api/lots/<int:lot_id>/spots')
api.add_resource(Spot, '/api/spots/<int:spot_id>')
api.add_resource(ReservationList, '/api/reservations')
api.add_resource(Reservation, '/api/reservations/<int:reservation_id>')
