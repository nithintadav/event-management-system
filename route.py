import os
import re
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_wtf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import mysql.connector

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"), static_folder=os.path.join(BASE_DIR, "static"))
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-fallback-change-me")

# CSRF protection for every POST form (base.html includes the hidden token)
csrf = CSRFProtect(app)

UPLOAD_FOLDER = os.path.join(app.static_folder, "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB banner limit


# ---------------- DATABASE CONNECTION ----------------
def get_db():
    try:
        return mysql.connector.connect(
            host=os.environ.get("DB_HOST", "localhost"),
            user=os.environ.get("DB_USER", "root"),
            password=os.environ.get("DB_PASSWORD", "sql@000"),
            database=os.environ.get("DB_NAME", "event_db2"),
            port=int(os.environ.get("DB_PORT", 3306)),
        )
    except mysql.connector.Error as exc:
        raise RuntimeError(f"Database connection failed: {exc}") from exc


def initialize_database():
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SHOW TABLES LIKE 'users'")
    if not cursor.fetchone():
        cursor.execute("""
            CREATE TABLE users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(150) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                phone VARCHAR(20) DEFAULT NULL,
                profile_image VARCHAR(255) DEFAULT NULL,
                role ENUM('user', 'admin') NOT NULL DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB
        """)
        db.commit()
        cursor.close()
        db.close()
        return

    def column_exists(table_name, column_name):
        cursor.execute(f"SHOW COLUMNS FROM {table_name} LIKE %s", (column_name,))
        return cursor.fetchone() is not None

    if column_exists("users", "password"):
        cursor.execute("SELECT id, password FROM users WHERE password IS NOT NULL AND password != '' LIMIT 1")
        legacy_user = cursor.fetchone()
        if legacy_user:
            cursor.execute("UPDATE users SET password_hash = password WHERE password_hash IS NULL OR password_hash = ''")
        cursor.execute("ALTER TABLE users DROP COLUMN password")

    if not column_exists("users", "password_hash"):
        cursor.execute("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255) NOT NULL DEFAULT ''")
    if not column_exists("users", "phone"):
        cursor.execute("ALTER TABLE users ADD COLUMN phone VARCHAR(20) DEFAULT NULL")
    if not column_exists("users", "profile_image"):
        cursor.execute("ALTER TABLE users ADD COLUMN profile_image VARCHAR(255) DEFAULT NULL")
    if not column_exists("users", "role"):
        cursor.execute("ALTER TABLE users ADD COLUMN role ENUM('user', 'admin') NOT NULL DEFAULT 'user'")
    if not column_exists("users", "created_at"):
        cursor.execute("ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

    db.commit()
    cursor.close()
    db.close()


initialize_database()


# ---------------- HELPERS ----------------
def login_required(role=None):
    """Call at the top of a view; returns a redirect or None if allowed through."""
    if "user_id" not in session:
        return redirect(url_for("login"))
    if role and session.get("role") != role:
        return redirect(url_for("login"))
    return None


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def slugify(title):
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return f"{slug}-{int(datetime.utcnow().timestamp())}"


def save_banner(file_storage):
    """Saves an uploaded banner image and returns its stored filename, or None."""
    if not file_storage or file_storage.filename == "":
        return None
    if not allowed_file(file_storage.filename):
        flash("Banner must be an image file (png, jpg, jpeg, gif, webp).", "warning")
        return None
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    filename = secure_filename(f"{int(datetime.utcnow().timestamp())}_{file_storage.filename}")
    file_storage.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
    return filename


# ---------------- HOME ----------------
@app.route("/")
def home():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT events.*, categories.name AS category_name,
               (events.max_seats - (
                   SELECT COUNT(*) FROM bookings
                   WHERE bookings.event_id = events.id AND bookings.status = 'confirmed'
               )) AS seats_left
        FROM events
        LEFT JOIN categories ON events.category_id = categories.id
        WHERE events.event_date >= CURDATE()
        ORDER BY events.event_date ASC
        LIMIT 6
    """)
    events = cursor.fetchall()
    cursor.close()
    db.close()
    return render_template("index.html", events=events)


# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("register.html")

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "danger")
            return render_template("register.html")

        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT id FROM users WHERE email=%s", (email,))
        if cursor.fetchone():
            cursor.close()
            db.close()
            flash("An account with that email already exists.", "danger")
            return render_template("register.html")

        password_hash = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, 'user')",
            (name, email, password_hash),
        )
        db.commit()

        session["user_id"] = cursor.lastrowid
        session["name"] = name
        session["email"] = email
        session["role"] = "user"

        cursor.close()
        db.close()
        flash(f"Welcome, {name}! Your account has been created.", "success")
        return redirect(url_for("dashboard"))

    return render_template("register.html")


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        cursor.close()
        db.close()

        if user:
            stored_hash = user.get("password_hash", "") or ""
            password_ok = False
            if stored_hash:
                try:
                    password_ok = check_password_hash(stored_hash, password)
                except Exception:
                    password_ok = False

            if password_ok:
                session["user_id"] = user["id"]
                session["name"] = user["name"]
                session["email"] = user["email"]
                session["role"] = user["role"]

                if user["role"] == "admin":
                    return redirect(url_for("admin"))
                return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "danger")
        return render_template("login.html")

    return render_template("login.html")


# ---------------- USER DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    guard = login_required(role="user")
    if guard:
        return guard

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT events.title, events.event_date, events.event_time, events.venue
        FROM bookings
        JOIN events ON bookings.event_id = events.id
        WHERE bookings.user_id=%s AND bookings.status='confirmed' AND events.event_date >= CURDATE()
        ORDER BY events.event_date ASC
        LIMIT 5
    """, (session["user_id"],))
    upcoming_bookings = cursor.fetchall()

    cursor.execute("""
        SELECT COUNT(*) AS total FROM bookings WHERE user_id=%s AND status='confirmed'
    """, (session["user_id"],))
    total_bookings = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total FROM bookings WHERE user_id=%s AND status='cancelled'
    """, (session["user_id"],))
    total_cancelled = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT message, is_read, created_at FROM notifications
        WHERE user_id=%s ORDER BY created_at DESC LIMIT 5
    """, (session["user_id"],))
    notifications = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "dashboard.html",
        name=session["name"],
        upcoming_bookings=upcoming_bookings,
        total_bookings=total_bookings,
        total_cancelled=total_cancelled,
        notifications=notifications,
    )


# ---------------- PROFILE EDIT ----------------
@app.route("/profile/edit", methods=["GET", "POST"])
def edit_profile():
    guard = login_required()
    if guard:
        return guard

    db = get_db()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        photo_file = request.files.get("profile_image")

        photo_filename = save_banner(photo_file)

        if photo_filename:
            cursor.execute("""
                UPDATE users SET name=%s, phone=%s, profile_image=%s WHERE id=%s
            """, (name, phone, photo_filename, session["user_id"]))
        else:
            cursor.execute("""
                UPDATE users SET name=%s, phone=%s WHERE id=%s
            """, (name, phone, session["user_id"]))

        db.commit()
        session["name"] = name
        cursor.close()
        db.close()
        flash("Profile updated.", "success")
        return redirect(url_for("dashboard"))

    cursor.execute("SELECT name, email, phone, profile_image FROM users WHERE id=%s",
                   (session["user_id"],))
    user = cursor.fetchone()
    cursor.close()
    db.close()
    return render_template("edit_profile.html", user=user)


# ---------------- ADMIN DASHBOARD ----------------
@app.route("/admin")
def admin():
    guard = login_required(role="admin")
    if guard:
        return guard

    db = get_db()
    cursor = db.cursor(dictionary=True)

    search_user = request.args.get("search_user", "").strip()
    search_event = request.args.get("search_event", "").strip()

    user_query = "SELECT id, name, email, role FROM users WHERE 1=1"
    user_params = []
    if search_user:
        user_query += " AND (name LIKE %s OR email LIKE %s)"
        user_params.extend([f"%{search_user}%", f"%{search_user}%"])
    user_query += " ORDER BY id DESC"
    cursor.execute(user_query, tuple(user_params))
    users = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) AS total FROM users")
    total_users = cursor.fetchone()["total"]
    cursor.execute("SELECT COUNT(*) AS total FROM users WHERE role='admin'")
    total_admins = cursor.fetchone()["total"]
    cursor.execute("SELECT COUNT(*) AS total FROM users WHERE role='user'")
    total_normal_users = cursor.fetchone()["total"]

    event_query = """
        SELECT events.*, categories.name AS category_name,
               COUNT(CASE WHEN bookings.status='confirmed' THEN 1 END) AS booking_count
        FROM events
        LEFT JOIN categories ON events.category_id = categories.id
        LEFT JOIN bookings ON events.id = bookings.event_id
        WHERE 1=1
    """
    event_params = []
    if search_event:
        event_query += " AND events.title LIKE %s"
        event_params.append(f"%{search_event}%")
    event_query += " GROUP BY events.id ORDER BY events.event_date ASC"
    cursor.execute(event_query, tuple(event_params))
    events = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) AS total FROM events")
    total_events = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total FROM bookings WHERE status='confirmed'
    """)
    total_bookings = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT events.title, COUNT(bookings.id) AS booking_count
        FROM events
        JOIN bookings ON events.id = bookings.event_id
        WHERE bookings.status='confirmed'
        GROUP BY events.id
        ORDER BY booking_count DESC
        LIMIT 1
    """)
    most_booked = cursor.fetchone()

    cursor.execute("""
        SELECT users.name, events.title, bookings.booked_at
        FROM bookings
        JOIN users ON bookings.user_id = users.id
        JOIN events ON bookings.event_id = events.id
        WHERE bookings.status='confirmed'
        ORDER BY bookings.booked_at DESC
        LIMIT 5
    """)
    recent_registrations = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template(
        "admin.html",
        name=session["name"],
        users=users,
        events=events,
        total_users=total_users,
        total_admins=total_admins,
        total_normal_users=total_normal_users,
        total_events=total_events,
        total_bookings=total_bookings,
        most_booked=most_booked,
        recent_registrations=recent_registrations,
        search_user=search_user,
        search_event=search_event,
    )


# ---------------- DELETE USER ----------------
@app.route("/delete_user/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    guard = login_required(role="admin")
    if guard:
        return guard

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT role FROM users WHERE id=%s", (user_id,))
    user = cursor.fetchone()

    if user and user[0] == "admin":
        cursor.close()
        db.close()
        flash("Admin accounts cannot be deleted.", "warning")
        return redirect(url_for("admin"))

    cursor.execute("DELETE FROM users WHERE id=%s", (user_id,))
    db.commit()
    cursor.close()
    db.close()
    flash("User deleted.", "success")
    return redirect(url_for("admin"))


# ---------------- VIEW EVENTS ----------------
@app.route("/events")
def view_events():
    guard = login_required()
    if guard:
        return guard

    search = request.args.get("search", "")
    location = request.args.get("location", "")
    date = request.args.get("date", "")
    category = request.args.get("category", "")
    sort = request.args.get("sort", "date_asc")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    query = """
        SELECT events.*, categories.name AS category_name,
               (events.max_seats - (
                   SELECT COUNT(*) FROM bookings b
                   WHERE b.event_id = events.id AND b.status='confirmed'
               )) AS seats_left
        FROM events
        LEFT JOIN categories ON events.category_id = categories.id
        WHERE 1=1
    """
    params = []

    if search:
        query += " AND events.title LIKE %s"
        params.append(f"%{search}%")
    if location:
        query += " AND events.venue LIKE %s"
        params.append(f"%{location}%")
    if date:
        query += " AND events.event_date = %s"
        params.append(date)
    if category:
        query += " AND categories.name = %s"
        params.append(category)

    sort_map = {
        "date_asc": " ORDER BY events.event_date ASC",
        "date_desc": " ORDER BY events.event_date DESC",
        "fee_asc": " ORDER BY events.fee ASC",
        "fee_desc": " ORDER BY events.fee DESC",
    }
    query += sort_map.get(sort, sort_map["date_asc"])

    cursor.execute(query, tuple(params))
    events = cursor.fetchall()

    cursor.execute("SELECT name FROM categories ORDER BY name")
    categories = cursor.fetchall()

    wishlist_ids = set()
    if session.get("role") == "user":
        cursor.execute("SELECT event_id FROM wishlist WHERE user_id=%s", (session["user_id"],))
        wishlist_ids = {row["event_id"] for row in cursor.fetchall()}

    cursor.close()
    db.close()

    return render_template("events.html", events=events, categories=categories,
                            wishlist_ids=wishlist_ids, sort=sort)


# ---------------- EVENT DETAILS ----------------
@app.route("/event/<int:event_id>")
def event_details(event_id):
    guard = login_required()
    if guard:
        return guard

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT events.*, categories.name AS category_name,
               (events.max_seats - (
                   SELECT COUNT(*) FROM bookings b
                   WHERE b.event_id = events.id AND b.status='confirmed'
               )) AS seats_left
        FROM events
        LEFT JOIN categories ON events.category_id = categories.id
        WHERE events.id=%s
    """, (event_id,))
    event = cursor.fetchone()

    if not event:
        cursor.close()
        db.close()
        flash("Event not found.", "warning")
        return redirect(url_for("view_events"))

    cursor.execute("SELECT image_path FROM event_gallery WHERE event_id=%s", (event_id,))
    gallery = cursor.fetchall()

    cursor.close()
    db.close()
    return render_template("event_details.html", event=event, gallery=gallery)


# ---------------- CREATE EVENT ----------------
@app.route("/create_event", methods=["GET", "POST"])
def create_event():
    guard = login_required(role="admin")
    if guard:
        return guard

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, name FROM categories ORDER BY name")
    categories = cursor.fetchall()

    if request.method == "POST":
        title = request.form["title"].strip()
        description = request.form["description"].strip()
        organizer = request.form["organizer"].strip()
        category_id = request.form.get("category_id") or None
        venue = request.form["venue"].strip()
        event_date = request.form["event_date"]
        event_time = request.form["event_time"]
        fee = request.form.get("fee", 0) or 0
        max_seats = request.form.get("max_seats", 0) or 0
        guidelines = request.form.get("guidelines", "").strip()
        contact_email = request.form.get("contact_email", "").strip()
        contact_phone = request.form.get("contact_phone", "").strip()

        banner_filename = save_banner(request.files.get("banner_image"))
        slug = slugify(title)

        cursor2 = db.cursor()
        cursor2.execute("""
            INSERT INTO events
                (title, slug, description, organizer, category_id, venue,
                 event_date, event_time, fee, max_seats, banner_image,
                 guidelines, contact_email, contact_phone, created_by)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (title, slug, description, organizer, category_id, venue,
              event_date, event_time, fee, max_seats, banner_filename,
              guidelines, contact_email, contact_phone, session["user_id"]))
        db.commit()
        cursor2.close()
        cursor.close()
        db.close()

        flash("Event created successfully.", "success")
        return redirect(url_for("admin"))

    cursor.close()
    db.close()
    return render_template("create_event.html", categories=categories)


# ---------------- CHECKOUT (simulated payment screen) ----------------
@app.route("/checkout/<int:event_id>")
def checkout(event_id):
    guard = login_required()
    if guard:
        return guard

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT events.*, categories.name AS category_name,
               (events.max_seats - (
                   SELECT COUNT(*) FROM bookings b
                   WHERE b.event_id = events.id AND b.status='confirmed'
               )) AS seats_left
        FROM events
        LEFT JOIN categories ON events.category_id = categories.id
        WHERE events.id=%s
    """, (event_id,))
    event = cursor.fetchone()

    if not event:
        cursor.close()
        db.close()
        flash("Event not found.", "warning")
        return redirect(url_for("view_events"))

    if event["seats_left"] <= 0:
        cursor.close()
        db.close()
        flash("Sorry, this event is fully booked.", "warning")
        return redirect(url_for("view_events"))

    cursor.execute("""
        SELECT status FROM bookings WHERE user_id=%s AND event_id=%s
    """, (session["user_id"], event_id))
    existing = cursor.fetchone()
    cursor.close()
    db.close()

    if existing and existing["status"] == "confirmed":
        flash("You've already registered for this event.", "info")
        return redirect(url_for("my_bookings"))

    # QR content is just a cosmetic reference string — no real payment gateway involved
    qr_payload = f"upi://pay?pa=eventra@upi&pn=Eventra&am={event['fee']}&tn=EVT{event_id}-{session['user_id']}&cu=INR"
    return render_template("checkout.html", event=event, qr_payload=qr_payload)


# ---------------- CONFIRM PAYMENT (simulated — no real charge happens) ----------------
@app.route("/confirm_payment/<int:event_id>", methods=["POST"])
def confirm_payment(event_id):
    guard = login_required()
    if guard:
        return guard

    payment_method = request.form.get("payment_method", "UPI")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT max_seats, (max_seats - (
            SELECT COUNT(*) FROM bookings WHERE event_id=%s AND status='confirmed'
        )) AS seats_left
        FROM events WHERE id=%s
    """, (event_id, event_id))
    event = cursor.fetchone()

    if not event or event["seats_left"] <= 0:
        cursor.close()
        db.close()
        flash("Sorry, this event is fully booked.", "warning")
        return redirect(url_for("view_events"))

    cursor.execute("""
        SELECT id, status FROM bookings WHERE user_id=%s AND event_id=%s
    """, (session["user_id"], event_id))
    existing = cursor.fetchone()

    if existing and existing["status"] == "confirmed":
        cursor.close()
        db.close()
        flash("You've already registered for this event.", "info")
        return redirect(url_for("my_bookings"))

    cursor2 = db.cursor()
    if existing:
        cursor2.execute("UPDATE bookings SET status='confirmed' WHERE id=%s", (existing["id"],))
        booking_id = existing["id"]
    else:
        cursor2.execute(
            "INSERT INTO bookings (user_id, event_id, status) VALUES (%s, %s, 'confirmed')",
            (session["user_id"], event_id),
        )
        booking_id = cursor2.lastrowid
    cursor2.close()

    db.commit()
    cursor.close()
    db.close()

    flash(f"Payment via {payment_method} successful — you're booked! 🎉", "success")
    return redirect(url_for("booking_confirmation", booking_id=booking_id))


# ---------------- REGISTRATION SLIP / CONFIRMATION ----------------
@app.route("/booking_confirmation/<int:booking_id>")
def booking_confirmation(booking_id):
    guard = login_required()
    if guard:
        return guard

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT bookings.id AS booking_id, bookings.booked_at, bookings.status,
               events.title, events.venue, events.event_date, events.event_time,
               events.fee, events.organizer,
               users.name AS attendee_name, users.email AS attendee_email
        FROM bookings
        JOIN events ON bookings.event_id = events.id
        JOIN users ON bookings.user_id = users.id
        WHERE bookings.id=%s AND bookings.user_id=%s
    """, (booking_id, session["user_id"]))
    booking = cursor.fetchone()
    cursor.close()
    db.close()

    if not booking:
        flash("Booking not found.", "warning")
        return redirect(url_for("my_bookings"))

    ticket_ref = f"EVT-{booking['booking_id']:06d}"
    return render_template("booking_confirmation.html", booking=booking, ticket_ref=ticket_ref)


# ---------------- MY BOOKINGS ----------------
@app.route("/my_bookings")
def my_bookings():
    guard = login_required()
    if guard:
        return guard

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT bookings.id AS booking_id, events.title, events.description,
               events.event_date, events.event_time, events.venue, bookings.status
        FROM bookings
        JOIN events ON bookings.event_id = events.id
        WHERE bookings.user_id = %s AND bookings.status='confirmed'
        ORDER BY events.event_date ASC
    """, (session["user_id"],))
    active_bookings = cursor.fetchall()

    cursor.execute("""
        SELECT bookings.id AS booking_id, events.title, events.event_date, events.venue
        FROM bookings
        JOIN events ON bookings.event_id = events.id
        WHERE bookings.user_id = %s AND bookings.status='cancelled'
        ORDER BY events.event_date DESC
    """, (session["user_id"],))
    cancelled_bookings = cursor.fetchall()

    cursor.close()
    db.close()
    return render_template("my_bookings.html", bookings=active_bookings,
                            cancelled_bookings=cancelled_bookings)


# ---------------- CANCEL BOOKING ----------------
@app.route("/cancel_booking/<int:booking_id>", methods=["POST"])
def cancel_booking(booking_id):
    guard = login_required()
    if guard:
        return guard

    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        UPDATE bookings SET status='cancelled'
        WHERE id=%s AND user_id=%s
    """, (booking_id, session["user_id"]))
    db.commit()
    cursor.close()
    db.close()
    flash("Booking cancelled.", "info")
    return redirect(url_for("my_bookings"))


# ---------------- WISHLIST ----------------
@app.route("/wishlist/toggle/<int:event_id>", methods=["POST"])
def toggle_wishlist(event_id):
    guard = login_required(role="user")
    if guard:
        return guard

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id FROM wishlist WHERE user_id=%s AND event_id=%s",
                   (session["user_id"], event_id))
    existing = cursor.fetchone()

    cursor2 = db.cursor()
    if existing:
        cursor2.execute("DELETE FROM wishlist WHERE id=%s", (existing["id"],))
        flash("Removed from wishlist.", "info")
    else:
        cursor2.execute("INSERT INTO wishlist (user_id, event_id) VALUES (%s,%s)",
                         (session["user_id"], event_id))
        flash("Added to wishlist.", "success")

    db.commit()
    cursor2.close()
    cursor.close()
    db.close()
    return redirect(request.referrer or url_for("view_events"))


# ---------------- VIEW PARTICIPANTS ----------------
@app.route("/participants/<int:event_id>")
def view_participants(event_id):
    guard = login_required(role="admin")
    if guard:
        return guard

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT users.name, users.email, bookings.booked_at
        FROM bookings
        JOIN users ON bookings.user_id = users.id
        WHERE bookings.event_id = %s AND bookings.status='confirmed'
    """, (event_id,))
    participants = cursor.fetchall()

    cursor.execute("SELECT title FROM events WHERE id=%s", (event_id,))
    event = cursor.fetchone()

    cursor.close()
    db.close()

    if not event:
        flash("Event not found.", "warning")
        return redirect(url_for("admin"))

    return render_template("participants.html", participants=participants,
                            event_title=event["title"])


# ---------------- EDIT EVENT ----------------
@app.route("/edit_event/<int:event_id>", methods=["GET", "POST"])
def edit_event(event_id):
    guard = login_required(role="admin")
    if guard:
        return guard

    db = get_db()
    cursor = db.cursor(dictionary=True)

    if request.method == "POST":
        title = request.form["title"].strip()
        description = request.form["description"].strip()
        organizer = request.form["organizer"].strip()
        category_id = request.form.get("category_id") or None
        venue = request.form["venue"].strip()
        event_date = request.form["event_date"]
        event_time = request.form["event_time"]
        fee = request.form.get("fee", 0) or 0
        max_seats = request.form.get("max_seats", 0) or 0
        guidelines = request.form.get("guidelines", "").strip()
        contact_email = request.form.get("contact_email", "").strip()
        contact_phone = request.form.get("contact_phone", "").strip()

        new_banner = save_banner(request.files.get("banner_image"))

        if new_banner:
            cursor.execute("""
                UPDATE events SET title=%s, description=%s, organizer=%s, category_id=%s,
                    venue=%s, event_date=%s, event_time=%s, fee=%s, max_seats=%s,
                    guidelines=%s, contact_email=%s, contact_phone=%s, banner_image=%s
                WHERE id=%s
            """, (title, description, organizer, category_id, venue, event_date,
                  event_time, fee, max_seats, guidelines, contact_email, contact_phone,
                  new_banner, event_id))
        else:
            cursor.execute("""
                UPDATE events SET title=%s, description=%s, organizer=%s, category_id=%s,
                    venue=%s, event_date=%s, event_time=%s, fee=%s, max_seats=%s,
                    guidelines=%s, contact_email=%s, contact_phone=%s
                WHERE id=%s
            """, (title, description, organizer, category_id, venue, event_date,
                  event_time, fee, max_seats, guidelines, contact_email, contact_phone,
                  event_id))

        db.commit()
        cursor.close()
        db.close()
        flash("Event updated.", "success")
        return redirect(url_for("admin"))

    cursor.execute("SELECT * FROM events WHERE id=%s", (event_id,))
    event = cursor.fetchone()
    cursor.execute("SELECT id, name FROM categories ORDER BY name")
    categories = cursor.fetchall()
    cursor.close()
    db.close()

    if not event:
        flash("Event not found.", "warning")
        return redirect(url_for("admin"))

    return render_template("edit_event.html", event=event, categories=categories)


# ---------------- DELETE EVENT ----------------
@app.route("/delete_event/<int:event_id>", methods=["POST"])
def delete_event(event_id):
    guard = login_required(role="admin")
    if guard:
        return guard

    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM events WHERE id=%s", (event_id,))
    db.commit()
    cursor.close()
    db.close()
    flash("Event deleted.", "info")
    return redirect(url_for("admin"))


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    flash("You've been logged out.", "info")
    return redirect(url_for("login"))


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
