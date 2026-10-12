# Vehicle Parking App

A **role-based parking management system** built with **Flask**, allowing admins and users to manage parking lots, spots, and bookings efficiently.

---

##  Features

- Role-based login: Admin and User
- Full RESTful JSON API (`/api/*`) for mobile apps and programmatic access
- Admin panel to manage lots, spots, and view summaries
- Users can book, release, and view their reservations
- Charts for data visualization using Chart.js
- Clean Bootstrap 5 UI

---

##  REST API Documentation

All API endpoints return JSON and accept either JSON or Form Data requests. Authentication is managed via session cookies.

### Authentication Endpoints
- `POST /api/auth/login` - Login (`email`, `password`)
- `POST /api/auth/register` - Register a new user
- `POST /api/auth/logout` - Clear session
- `GET /api/auth/me` - Get currently authenticated user details

### Parking Lots & Spots
- `GET /api/lots?q=<query>` - List all parking lots with live availability
- `GET /api/lots/<lot_id>` - Get parking lot details with spots list
- `POST /api/lots` - Create new parking lot *(Admin only)*
- `PUT /api/lots/<lot_id>` - Update parking lot / resize spots *(Admin only)*
- `DELETE /api/lots/<lot_id>` - Delete parking lot *(Admin only)*
- `POST /api/lots/bulk-delete` - Bulk delete lots with `lot_ids: [...]` *(Admin only)*
- `POST /api/lots/<lot_id>/spots` - Add a spot to lot *(Admin only)*
- `DELETE /api/spots/<spot_id>` - Delete spot *(Admin only)*
- `GET /api/spots/<spot_id>/details` - View spot & latest reservation *(Admin only)*

### Bookings & Reservations
- `GET /api/bookings?filter=all|not_released|released` - Get current user's bookings
- `POST /api/bookings` - Book a slot in lot (`lot_id`, `vehicle_number`)
- `POST /api/bookings/<reservation_id>/release` - Release parked vehicle & compute final bill

### Admin Metrics & Analytics
- `GET /api/admin/summary` - 7-day revenue, bookings trend, top location, and spot counts
- `GET /api/admin/users?q=<query>` - List & search registered users
- `GET /api/admin/search?filter_by=...&query=...` - Multi-entity advanced search

### User Metrics & Profile
- `GET /api/user/summary` - User's 7-day spending trends, frequency, and lot statistics
- `GET /api/profile` - View user/admin profile
- `PUT /api/profile` - Update profile information and password

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

