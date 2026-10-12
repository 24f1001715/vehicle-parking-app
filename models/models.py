import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///parking.sqlite3')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


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
    spot_number = db.Column(db.Integer, nullable=False)  
    status = db.Column(db.String(1), default='A')  
    reservation = db.relationship('Reservation', backref='spot', uselist=False)

class Reservation(db.Model):
    __tablename__ = 'reservation'
    id = db.Column(db.Integer, primary_key=True)
    
    spot_id = db.Column(
        db.Integer,
        db.ForeignKey('parking_spot.id', ondelete='SET DEFAULT'),
        nullable=True,
        default=0
    )
    lot_id = db.Column(
        db.Integer,
        db.ForeignKey('parking_lot.id', ondelete='SET DEFAULT'),
        nullable=True,
        default=0
    )
    user_email = db.Column(
        db.String(120),
        db.ForeignKey('user.email_id'),
        nullable=False
    )
    parking_timestamp = db.Column(db.String(50), nullable=False)
    leaving_timestamp = db.Column(db.String(50), nullable=True)
    cost_per_hour = db.Column(db.Float)
    total_cost = db.Column(db.Float, nullable=True)
    vehicle_number = db.Column(db.String(20), nullable=False, default='Unknown')

    user = db.relationship('User', backref='reservations')



if __name__ == '__main__':
    with app.app_context():
        db.drop_all()  
        db.create_all()

        if not Admin.query.first():
            admin_email = os.getenv('ADMIN_EMAIL', 'admin@example.com')
            admin_password = os.getenv('ADMIN_PASSWORD', 'Admin@12345')
            admin_fullname = os.getenv('ADMIN_FULLNAME', 'Super Admin')
            admin = Admin(
                email_id=admin_email,
                fullname=admin_fullname,
                password=generate_password_hash(admin_password),
                address="Admin HQ",
                pincode="600000"
            )
            db.session.add(admin)

        user_data = [
            ("vidhya@example.com", "Vidhya"),
            ("vicky@example.com", "Vicky"),
            ("meera@example.com", "Meera"),
            ("rahul@example.com", "Rahul"),
            ("ananya@example.com", "Ananya"),
            ("karthik@example.com", "Karthik"),
            ("isha@example.com", "Isha"),
            ("sanjay@example.com", "Sanjay"),
            ("neha@example.com", "Neha"),
            ("vivek@example.com", "Vivek"),
            ("tara@example.com", "Tara"),
            ("rohan@example.com", "Rohan"),
            ("diya@example.com", "Diya"),
            ("amit@example.com", "Amit"),
            ("shruti@example.com", "Shruti"),
            ("dev@example.com", "Dev"),
            ("riya@example.com", "Riya"),
            ("manav@example.com", "Manav"),
            ("simran@example.com", "Simran"),
            ("aakash@example.com", "Aakash"),
        ]

        parking_lot_data = [
            "Central Mall", "Phoenix Marketcity", "Spencer Plaza", "Express Avenue",
            "Forum Vijaya", "Marina Plaza", "City Centre", "Skywalk Mall",
            "Tidel Park", "Ascendas", "DLF IT Park", "One India Bulls",
            "Perungudi Hub", "Tambaram Square", "Anna Nagar Plaza", "Kodambakkam Corner",
            "Velachery Point", "Adyar Bay", "Ambattur Junction", "Mylapore Tower"
        ]

        if not User.query.first():
            for i, (email, name) in enumerate(user_data):
                user = User(
                    email_id=email,
                    fullname=name,
                    password=generate_password_hash("12345678"),
                    address=f"{100 + i} Example Street",
                    pincode=f"600{str(i+1).zfill(3)}"
                )
                db.session.add(user)

        if not ParkingLot.query.first():
            for i, lot_name in enumerate(parking_lot_data):
                lot = ParkingLot(
                    prime_location_name=lot_name,
                    address=f"{i+1} Main Road, Chennai",
                    pin_code=f"700{str(i+1).zfill(3)}",
                    price=15 + (i % 5) * 5,
                    max_spots=10
                )
                db.session.add(lot)
                db.session.commit() 

                for j in range(1, lot.max_spots + 1):
                    spot = ParkingSpot(lot_id=lot.id, spot_number=j)
                    db.session.add(spot)

        db.session.commit()
        print("Database seeded with 20 users and 20 named parking lots.")
