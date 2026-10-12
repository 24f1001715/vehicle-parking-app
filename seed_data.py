import os
import random
import math
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

from app import app
from models.models import db, Admin, User, ParkingLot, ParkingSpot, Reservation

load_dotenv()


def seed_database():
    with app.app_context():
        print("Resetting database...")
        db.drop_all()
        db.create_all()

        # 1. Seed Admin
        admin_email = os.getenv('ADMIN_EMAIL', 'admin@example.com')
        admin_password = os.getenv('ADMIN_PASSWORD', 'Admin@12345')
        admin_fullname = os.getenv('ADMIN_FULLNAME', 'Super Admin')

        admin = Admin(
            email_id=admin_email,
            fullname=admin_fullname,
            password=generate_password_hash(admin_password),
            address="Anna Salai, Chennai, TN",
            pincode="600002"
        )
        db.session.add(admin)

        # 2. Seed Realistic Users
        users_meta = [
            ("vidhya@example.com", "Vidhya Raman", "45 Besant Nagar Beach Rd, Chennai", "600090"),
            ("vicky@example.com", "Vicky Vignesh", "12 Usman Road, T. Nagar, Chennai", "600017"),
            ("meera@example.com", "Meera Krishnan", "88 Cathedral Road, Gopalapuram, Chennai", "600086"),
            ("rahul@example.com", "Rahul Sharma", "102 OMR IT Expressway, Sholinganallur, Chennai", "600119"),
            ("ananya@example.com", "Ananya Iyer", "24 2nd Avenue, Anna Nagar, Chennai", "600040"),
            ("karthik@example.com", "Karthik Subramanian", "15 Velachery Bypass Road, Chennai", "600042"),
            ("isha@example.com", "Isha Patel", "7 Kasturi Ranga Road, Alwarpet, Chennai", "600018"),
            ("sanjay@example.com", "Sanjay Kumar", "63 GST Road, Guindy, Chennai", "600032"),
            ("neha@example.com", "Neha Gupta", "31 Greenways Road, R.A. Puram, Chennai", "600028"),
            ("vivek@example.com", "Vivek Menon", "54 Gandhi Mandapam Rd, Kotturpuram, Chennai", "600085"),
            ("tara@example.com", "Tara Balaji", "9 Montieth Road, Egmore, Chennai", "600008"),
            ("rohan@example.com", "Rohan Verma", "77 Nelson Manickam Rd, Aminjikarai, Chennai", "600029"),
            ("diya@example.com", "Diya Sundar", "19 Eldams Road, Teynampet, Chennai", "600018"),
            ("amit@example.com", "Amit Mukherjee", "33 Haddows Road, Nungambakkam, Chennai", "600006"),
            ("shruti@example.com", "Shruti Raghavan", "42 Santhome High Road, Mylapore, Chennai", "600004"),
            ("dev@example.com", "Dev Narayanan", "8 1st Seaward Road, Valmiki Nagar, Thiruvanmiyur", "600041"),
            ("riya@example.com", "Riya Sen", "11 Arcot Road, Vadapalani, Chennai", "600026"),
            ("manav@example.com", "Manav Sethi", "28 Sterling Road, Nungambakkam, Chennai", "600034"),
            ("simran@example.com", "Simran Kaur", "90 Poonamallee High Rd, Kilpauk, Chennai", "600010"),
            ("aakash@example.com", "Aakash Reddy", "5 East Coast Road, Thiruvanmiyur, Chennai", "600041"),
        ]

        # Password meeting strong criteria: "Password123*"
        user_pw_hash = generate_password_hash("12345678")
        created_users = []
        for email, name, addr, pin in users_meta:
            u = User(
                email_id=email,
                fullname=name,
                password=user_pw_hash,
                address=addr,
                pincode=pin
            )
            db.session.add(u)
            created_users.append(u)

        # 3. Seed Realistic Parking Lots & Spots
        lots_meta = [
            ("Express Avenue Mall", "Club House Rd, Royapettah", "600002", 40.0, 15),
            ("Phoenix Marketcity", "Velachery Main Rd, Indira Gandhi Nagar", "600042", 50.0, 20),
            ("Forum Vijaya Mall", "Arcot Rd, NSK Salai, Vadapalani", "600026", 45.0, 16),
            ("Tidel Park IT Complex", "Rajiv Gandhi Salai, Taramani", "600113", 30.0, 18),
            ("Marina Beach Parking Plaza", "Kamarajar Salai, Triplicane", "600005", 25.0, 25),
            ("Spencer Plaza Complex", "769 Anna Salai, Thousand Lights", "600002", 35.0, 12),
            ("Central Railway Square", "Kannappar Thidal, Periamet", "600003", 30.0, 20),
            ("Airport Terminal Deck", "GST Rd, Meenambakkam", "600027", 60.0, 24),
            ("VR Chennai Mall", "Jawaharlal Nehru Rd, Anna Nagar West", "600040", 50.0, 16),
            ("Besant Nagar Promenade", "6th Avenue, Besant Nagar", "600090", 30.0, 12),
            ("DLF Cybercity Lot", "Mount Poonamallee High Rd, Manapakkam", "600089", 35.0, 15),
            ("Adyar Signal Transit Deck", "Sardar Patel Rd, Adyar", "600020", 30.0, 10),
        ]

        created_lots = []
        for name, addr, pin, price, max_spots in lots_meta:
            lot = ParkingLot(
                prime_location_name=name,
                address=addr,
                pin_code=pin,
                price=price,
                max_spots=max_spots
            )
            db.session.add(lot)
            created_lots.append(lot)

        db.session.commit()

        # Create spots for each lot
        lot_spots_map = {}
        for lot in created_lots:
            spots = []
            for num in range(1, lot.max_spots + 1):
                spot = ParkingSpot(lot_id=lot.id, spot_number=num, status='A')
                db.session.add(spot)
                spots.append(spot)
            lot_spots_map[lot.id] = spots

        db.session.commit()

        # 4. Realistic Vehicle Numbers pool
        vehicle_prefix = ["TN-01", "TN-02", "TN-05", "TN-07", "TN-09", "TN-10", "TN-14", "TN-22"]
        vehicle_series = ["AB", "BK", "CD", "EF", "GH", "JK", "MN", "XY", "ZZ"]
        
        def random_vehicle():
            return f"{random.choice(vehicle_prefix)}-{random.choice(vehicle_series)}-{random.randint(1000, 9999)}"

        # 5. Generate Past & Active Reservations (Realistic 7-Day History)
        now = datetime.now()
        reservations_created = 0

        # Create 70-80 historical completed reservations spread across past 7 days
        for day_offset in range(6, -1, -1):
            day_date = (now - timedelta(days=day_offset)).date()
            # 8 to 14 reservations per day
            daily_count = random.randint(8, 14)

            for _ in range(daily_count):
                user = random.choice(created_users)
                lot = random.choice(created_lots)
                spots = lot_spots_map[lot.id]
                spot = random.choice(spots)

                # Random parking time between 08:00 and 21:00
                hour = random.randint(8, 20)
                minute = random.randint(0, 59)
                start_dt = datetime(day_date.year, day_date.month, day_date.day, hour, minute, random.randint(0, 59))
                
                # Check if it's strictly in the past
                if start_dt > now - timedelta(hours=2):
                    continue

                duration_hours = random.randint(1, 6)
                end_dt = start_dt + timedelta(hours=duration_hours, minutes=random.randint(5, 30))
                billed_hours = max(math.ceil((end_dt - start_dt).total_seconds() / 3600), 1)
                total_cost = round(billed_hours * lot.price, 2)

                res = Reservation(
                    spot_id=spot.id,
                    lot_id=lot.id,
                    user_email=user.email_id,
                    parking_timestamp=start_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    leaving_timestamp=end_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    cost_per_hour=lot.price,
                    total_cost=total_cost,
                    vehicle_number=random_vehicle()
                )
                db.session.add(res)
                reservations_created += 1

        # 6. Create Active / Ongoing Reservations (Current vehicles parked)
        active_count = 0
        used_spots = set()

        for lot in created_lots:
            spots = lot_spots_map[lot.id]
            # Reserve 25% to 60% of spots in this lot
            num_to_reserve = random.randint(1, max(1, int(lot.max_spots * 0.45)))
            spots_to_reserve = random.sample(spots, num_to_reserve)

            for spot in spots_to_reserve:
                spot.status = 'R'
                user = random.choice(created_users)
                # Parked within the last 1 to 4 hours
                park_time = now - timedelta(hours=random.randint(0, 3), minutes=random.randint(5, 55))

                res = Reservation(
                    spot_id=spot.id,
                    lot_id=lot.id,
                    user_email=user.email_id,
                    parking_timestamp=park_time.strftime("%Y-%m-%d %H:%M:%S"),
                    leaving_timestamp=None,
                    cost_per_hour=lot.price,
                    total_cost=None,
                    vehicle_number=random_vehicle()
                )
                db.session.add(res)
                active_count += 1
                reservations_created += 1

        # Ensure our primary test accounts (vidhya@example.com & vicky@example.com) have both active and past bookings
        target_users = [u for u in created_users if u.email_id in ('vidhya@example.com', 'vicky@example.com')]
        for target_user in target_users:
            # Add one guaranteed active reservation for easy user testing
            available_spot = ParkingSpot.query.filter_by(status='A').first()
            if available_spot:
                available_spot.status = 'R'
                target_res = Reservation(
                    spot_id=available_spot.id,
                    lot_id=available_spot.lot_id,
                    user_email=target_user.email_id,
                    parking_timestamp=(now - timedelta(hours=1, minutes=20)).strftime("%Y-%m-%d %H:%M:%S"),
                    leaving_timestamp=None,
                    cost_per_hour=available_spot.lot.price,
                    total_cost=None,
                    vehicle_number=f"TN-01-SP-{random.randint(1000, 9999)}"
                )
                db.session.add(target_res)
                active_count += 1
                reservations_created += 1

        db.session.commit()

        print(f"\n=======================================================")
        print(f"DATABASE SEED COMPLETED SUCCESSFULLY!")
        print(f"=======================================================")
        print(f"Users created: {len(created_users)} + 1 Admin")
        print(f"Parking lots created: {len(created_lots)}")
        print(f"Total spots created: {sum(l.max_spots for l in created_lots)}")
        print(f"Total reservations seeded: {reservations_created}")
        print(f"Active vehicles currently parked: {active_count}")
        print(f"Admin login: {admin_email} / {admin_password}")
        print(f"User login: vidhya@example.com / 12345678")
        print(f"=======================================================\n")


if __name__ == '__main__':
    seed_database()
