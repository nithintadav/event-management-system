# 🎟️ Eventra — Event Management System

Eventra is a modern, feature-rich web application built with **Flask**, **MySQL**, and **Bootstrap 5**. It provides an end-to-end platform for discovering, organizing, and booking events, complete with dedicated User and Admin control portals, real-time metrics, interactive charts, and robust security.

---

## ✨ Features & Key Highlights

### 👤 User Features & Dashboard (`dashboard.html`)
- **Top Bar Profile Header**: Top right corner displays the user's uploaded profile picture or a stylish **photo symbol icon fallback** every time if no photo exists.
- **Universal Navigation**: Always-accessible **Go Back** and **Back to Home** buttons for effortless navigation across the app.
- **Personal Activity Summary**: Real-time counter cards for **Active Bookings**, **Cancelled Bookings**, and **Unread Notifications**.
- **Upcoming Events & Timeline**: Quick view of upcoming confirmed tickets with dates, times, and venue badges.
- **Notification Hub**: Stay updated with booking alerts and system notifications.
- **Profile Customization**: Update name, phone, and upload a profile photo.

### 🛡️ Admin Control Center (`admin.html`)
- **System Overview**: High-level metrics for Total Users, Active Events, Confirmed Bookings, and Admin/User ratios.
- **Visual Analytics (Chart.js)**:
  - 📊 **User Roles Breakdown** (Doughnut Chart)
  - 📈 **Bookings per Event** (Bar Chart)
  - 🏆 **Most Booked Event Spotlight**
- **User Directory Management**: Live search, role identification (`Administrator` vs `User`), and account deletion with protection for admin accounts.
- **Events Management Roster**: Create, edit, inspect event participants, search titles, manage seat limits, or remove events.
- **Top Right Admin Header**: Displays admin profile picture / photo symbol fallback and instant access to admin actions.

### 🔐 Security & Architecture
- **Password Security**: Hashing using Werkzeug (`pbkdf2:sha256`).
- **CSRF Protection**: Integrated `Flask-WTF` CSRF token verification across all forms.
- **SQL Injection Prevention**: Parameterized queries using `mysql.connector`.
- **Role-Based Access Control (RBAC)**: Decorators guarding routes based on user roles (`user` / `admin`).

---

## 🛠️ Technology Stack

- **Backend**: Python 3.x, Flask, Flask-WTF, Werkzeug
- **Database**: MySQL Server
- **Frontend**: HTML5, CSS3, JavaScript (ES6+), Bootstrap 5, Chart.js
- **Design Systems**: Custom CSS variables, responsive glassmorphism cards, dark/light theme toggle

---

## 🚀 Getting Started & Installation

### 1. Prerequisites
- Python 3.8+ installed
- MySQL Server installed and running

### 2. Clone / Setup Workspace
Navigate to the project root directory:
```bash
cd "c:\Users\LENOVO\OneDrive\Desktop\files"
```

### 3. Install Dependencies
Install all required Python packages from `requirements.txt`:
```bash
pip install -r requirements.txt
```

### 4. Database Setup & Configuration
Create a `.env` file in the root directory (or use the provided defaults):
```env
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=sql@000
DB_NAME=event_db2
DB_PORT=3306
SECRET_KEY=your-secret-key-here
```

Import `schema.sql` into MySQL if needed:
```sql
CREATE DATABASE IF NOT EXISTS event_db2;
USE event_db2;
-- Run schema.sql script content
```
*(Note: `route.py` automatically initializes missing database tables and columns on server startup.)*

### 5. Launch the Application
Run the Flask application:
```bash
python route.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 📁 Project Structure

```
.
├── route.py                  # Main Flask application, routes, DB connection & initialization
├── schema.sql                # SQL schema for users, categories, events, bookings, notifications
├── check_db_connection.py    # Utility script to test database connectivity
├── requirements.txt          # Python dependencies
├── static/
│   ├── css/
│   │   └── style.css         # Theme design tokens, badges, dark mode & layout utilities
│   └── uploads/              # Uploaded user profile photos & event banners
└── templates/
    ├── base.html             # Base layout template (Navbar, Flash Messages, Footer, Theme toggle)
    ├── index.html            # Public homepage with featured events & categories
    ├── dashboard.html        # Reconstructed User Dashboard with profile avatar & Go Back nav
    ├── admin.html            # Reconstructed Admin Control Center with metrics, charts & rosters
    ├── create_event.html     # Form for creating new events
    ├── edit_event.html       # Form for modifying existing events
    ├── edit_profile.html     # Profile photo & contact info edit page
    ├── events.html           # Event discovery page with filters & search
    ├── event_details.html    # Detailed event view & seat selection
    ├── checkout.html         # Booking checkout & payment simulation
    ├── my_bookings.html      # User ticket history & cancellation management
    ├── participants.html    # Admin view of registered attendees per event
    ├── login.html            # Account authentication page
    └── register.html         # New user registration page
```

---

## 📜 License
This project is built for educational and placement demonstration purposes.
