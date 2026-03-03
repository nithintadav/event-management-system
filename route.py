from flask import Flask, render_template, request, redirect, session
import mysql.connector

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ---------------- DATABASE CONNECTION ----------------
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="sql@000",
        database="event_db",
        port=3307
    )

# ---------------- HOME ----------------
@app.route('/')
def home():
    return redirect('/login')

# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        db = get_db()
        cursor = db.cursor(dictionary=True)

        # Check if user already exists
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            cursor.close()
            db.close()
            return render_template("register.html", message="User already exists")

        # Insert new user (default role = user)
        cursor.execute(
            "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, 'user')",
            (name, email, password)
        )
        db.commit()

        # Auto login after registration
        session['user_id'] = cursor.lastrowid
        session['name'] = name
        session['email'] = email
        session['role'] = 'user'

        cursor.close()
        db.close()

        return redirect('/dashboard')

    return render_template("register.html")

# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        db = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM users WHERE email=%s AND password=%s",
            (email, password)
        )
        user = cursor.fetchone()

        cursor.close()
        db.close()

        if user:
            session['user_id'] = user['id']
            session['name'] = user['name']
            session['email'] = user['email']
            session['role'] = user['role']

            # Role-based redirect
            if user['role'] == 'admin':
                return redirect('/admin')
            else:
                return redirect('/dashboard')

        return render_template("login.html", message="Invalid Credentials")

    return render_template("login.html")

# ---------------- USER DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    if 'user_id' in session and session.get('role') == 'user':
        return render_template("dashboard.html", name=session['name'])
    return redirect('/login')

# ---------------- ADMIN DASHBOARD ----------------
# ---------------- ADMIN DASHBOARD ----------------
@app.route('/admin')
def admin():
    if 'user_id' in session and session.get('role') == 'admin':

        db = get_db()
        cursor = db.cursor(dictionary=True)

        # ---------------- USERS ----------------
        cursor.execute("SELECT id, name, email, role FROM users")
        users = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) AS total FROM users")
        total_users = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) AS total FROM users WHERE role='admin'")
        total_admins = cursor.fetchone()['total']

        cursor.execute("SELECT COUNT(*) AS total FROM users WHERE role='user'")
        total_normal_users = cursor.fetchone()['total']

        # ---------------- EVENTS ----------------
        cursor.execute("SELECT * FROM events ORDER BY event_date ASC")
        events = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) AS total FROM events")
        total_events = cursor.fetchone()['total']

        cursor.close()
        db.close()

        return render_template(
            "admin.html",
            name=session['name'],
            users=users,
            events=events,
            total_users=total_users,
            total_admins=total_admins,
            total_normal_users=total_normal_users,
            total_events=total_events
        )

    return redirect('/login')

# ---------------- DELETE USER ----------------
@app.route('/delete_user/<int:user_id>')
def delete_user(user_id):
    if 'user_id' in session and session.get('role') == 'admin':

        db = get_db()
        cursor = db.cursor()

        # Prevent deleting admin account
        cursor.execute("SELECT role FROM users WHERE id=%s", (user_id,))
        user = cursor.fetchone()

        if user and user[0] == 'admin':
            cursor.close()
            db.close()
            return "Admin cannot be deleted"

        cursor.execute("DELETE FROM users WHERE id=%s", (user_id,))
        db.commit()

        cursor.close()
        db.close()

        return redirect('/admin')

    return redirect('/login')
#----------------- VIEW EVENTS ----------------
@app.route('/events')
def view_events():
    if 'user_id' in session:

        db = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute("SELECT * FROM events ORDER BY event_date ASC")
        events = cursor.fetchall()

        cursor.close()
        db.close()

        return render_template("events.html", events=events)

    return redirect('/login')

# ---------------- CREATE EVENT ----------------
@app.route('/create_event', methods=['GET', 'POST'])
def create_event():
    if 'user_id' in session and session.get('role') == 'admin':

        if request.method == 'POST':
            title = request.form['title']
            description = request.form['description']
            event_date = request.form['event_date']
            location = request.form['location']

            db = get_db()
            cursor = db.cursor()

            cursor.execute("""
                INSERT INTO events (title, description, event_date, location, created_by)
                VALUES (%s, %s, %s, %s, %s)
            """, (title, description, event_date, location, session['user_id']))

            db.commit()
            cursor.close()
            db.close()

            return redirect('/admin')

        return render_template("create_event.html")

    return redirect('/login')
# ---------------- BOOK EVENT ----------------
@app.route('/book_event/<int:event_id>')
def book_event(event_id):
    if 'user_id' in session:

        db = get_db()
        cursor = db.cursor()

        # Prevent duplicate booking
        cursor.execute("""
            SELECT * FROM bookings 
            WHERE user_id=%s AND event_id=%s
        """, (session['user_id'], event_id))

        existing = cursor.fetchone()

        if existing:
            cursor.close()
            db.close()
            return "You already registered for this event"

        # Insert booking
        cursor.execute("""
            INSERT INTO bookings (user_id, event_id)
            VALUES (%s, %s)
        """, (session['user_id'], event_id))

        db.commit()
        cursor.close()
        db.close()

        return "Event Registered Successfully 🎉"

    return redirect('/login')
# ---------------- MY BOOKINGS ----------------
# ---------------- MY BOOKINGS ----------------
@app.route('/my_bookings')
def my_bookings():
    if 'user_id' in session:

        db = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT bookings.id AS booking_id,
                   events.title,
                   events.description,
                   events.event_date,
                   events.location
            FROM bookings
            JOIN events ON bookings.event_id = events.id
            WHERE bookings.user_id = %s
            ORDER BY events.event_date ASC
        """, (session['user_id'],))

        bookings = cursor.fetchall()

        cursor.close()
        db.close()

        return render_template("my_bookings.html", bookings=bookings)

    return redirect('/login')
# ---------------- CANCEL BOOKING ----------------
@app.route('/cancel_booking/<int:booking_id>')
def cancel_booking(booking_id):
    if 'user_id' in session:

        db = get_db()
        cursor = db.cursor()

        # Ensure user cancels only their own booking
        cursor.execute("""
            DELETE FROM bookings 
            WHERE id=%s AND user_id=%s
        """, (booking_id, session['user_id']))

        db.commit()
        cursor.close()
        db.close()

        return redirect('/my_bookings')

    return redirect('/login')
# ---------------- VIEW PARTICIPANTS ----------------
@app.route('/participants/<int:event_id>')
def view_participants(event_id):
    if 'user_id' in session and session.get('role') == 'admin':

        db = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT users.name, users.email
            FROM bookings
            JOIN users ON bookings.user_id = users.id
            WHERE bookings.event_id = %s
        """, (event_id,))

        participants = cursor.fetchall()

        # Get event title
        cursor.execute("SELECT title FROM events WHERE id=%s", (event_id,))
        event = cursor.fetchone()

        cursor.close()
        db.close()

        return render_template(
            "participants.html",
            participants=participants,
            event_title=event['title']
        )

    return redirect('/login')

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)