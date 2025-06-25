from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parking.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ------------------------ Models ------------------------

class Admin(db.Model):
    __tablename__ = 'admin'
    id = db.Column(db.Integer, primary_key=True)
    email_id = db.Column(db.String(100), unique=True, nullable=False)
    fullname = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(200), nullable=True)
    pincode = db.Column(db.String(10), nullable=True)

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email_id = db.Column(db.String(100), unique=True, nullable=False)
    fullname = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(200), nullable=True)
    pincode = db.Column(db.String(10), nullable=True)

class ParkingLot(db.Model):
    __tablename__ = 'parking_lot'
    id = db.Column(db.Integer, primary_key=True)
    prime_location_name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200))
    pin_code = db.Column(db.String(10))
    price = db.Column(db.Float, nullable=False)
    max_spots = db.Column(db.Integer, nullable=False)
    spots = db.relationship('ParkingSpot', backref='lot', cascade="all, delete", lazy=True)
    reservations = db.relationship('Reservation', backref='lot', lazy=True)

class ParkingSpot(db.Model):
    __tablename__ = 'parking_spot'
    id = db.Column(db.Integer, primary_key=True)
    lot_id = db.Column(db.Integer, db.ForeignKey('parking_lot.id'), nullable=False)
    spot_number = db.Column(db.Integer, nullable=False)  # Sequential number per lot
    status = db.Column(db.String(1), default='A')  # A = Available, R = Reserved
    reservation = db.relationship('Reservation', backref='spot', uselist=False)

class Reservation(db.Model):
    __tablename__ = 'reservation'
    id = db.Column(db.Integer, primary_key=True)
    spot_id = db.Column(db.Integer, db.ForeignKey('parking_spot.id'), nullable=False, unique=True)
    lot_id = db.Column(db.Integer, db.ForeignKey('parking_lot.id'), nullable=False)
    user_email = db.Column(db.String(120), db.ForeignKey('user.email_id'), nullable=False)
    parking_timestamp = db.Column(db.String(50), nullable=False)
    leaving_timestamp = db.Column(db.String(50), nullable=True)
    cost_per_hour = db.Column(db.Float)

    user = db.relationship('User', backref='reservations')

# ------------------------ Database Initialization ------------------------

if __name__ == '__main__':
    with app.app_context():
        db.drop_all()  # Only use this if you want to recreate everything
        db.create_all()

        # Add a default admin
        if not Admin.query.first():
            admin = Admin(
                email_id="admin@example.com",
                fullname="Super Admin",
                password=generate_password_hash("12345678"),
                address="Admin HQ",
                pincode="600000"
            )
            db.session.add(admin)

        # Add a sample user
        if not User.query.first():
            user1 = User(
                email_id="vicky@example.com",
                fullname="Vicky",
                password=generate_password_hash("12345678"),
                address="123 User Lane",
                pincode="600001"
            )
            db.session.add(user1)

        # Optional: Add a sample parking lot and spots
        if not ParkingLot.query.first():
            lot = ParkingLot(
                prime_location_name="Central Mall",
                address="123 Main Road, Chennai",
                pin_code="600001",
                price=20.0,
                max_spots=10
            )
            db.session.add(lot)
            db.session.commit()

            for i in range(1, lot.max_spots + 1):
                spot = ParkingSpot(lot_id=lot.id, spot_number=i)
                db.session.add(spot)

        db.session.commit()
        print("Database initialized and seeded.")
