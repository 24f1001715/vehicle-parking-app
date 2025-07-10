# Vehicle Parking App

A **role-based parking management system** built with **Flask**, allowing admins and users to manage parking lots, spots, and bookings efficiently.

---

##  Features

- Role-based login: Admin and User
- Admin panel to manage lots, spots, and view summaries
- Users can book, release, and view their reservations
- Charts for data visualization using Chart.js
- Clean Bootstrap 5 UI

---

##  Setup Instructions

### 1. Clone the Repository

```
git clone https://github.com/your-username/vehicle-parking-app.git
cd vehicle-parking-app
```

### 2. Create a Virtual Environment (optional but recommended)

```
python -m venv venv
source venv/bin/activate      # On macOS/Linux
venv\Scripts\activate         # On Windows
```

### 3. Install Dependencies

```
pip install -r requirements.txt
```

### 4. Initialize the Database

Run this once to generate the `parking.sqlite3` database and seed admin/users/parking lots:

```
python models/models.py
```

> This will drop and recreate the tables and seed 20 sample users and lots.

### 5. Run the App

```
python app.py
```

The app will be accessible at:  
[http://localhost:5000]

---

