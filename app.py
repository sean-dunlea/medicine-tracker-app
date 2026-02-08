#!/usr/bin/env python3
from flask import Flask, render_template, redirect, url_for, session, g, request, jsonify
# Server-side session management
from flask_session import Session
from forms import RegistrationForm, LoginForm, AddMedicationForm, AddMateForm, SymptomForm
from database import get_db, close_db
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import timedelta

app = Flask(__name__)
# Secret key for signing sessions to protect against CSRF attacks.
app.config["SECRET_KEY"] = "this-is-my-secret-key"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"

app.permanent_session_lifetime = timedelta(days=30) # This makes the lifetime of "Remember Me?" equal 30 days

# These are needed to send push notifications
import firebase_admin
from firebase_admin import credentials, messaging
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

# These are needed to schedule reminders
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timezone
import pytz # This is important for handling different timezones

Session(app)

# Ensures the database connection is closed after each request.
app.teardown_appcontext(close_db)

# This will run before every request. It avoids repeating session.get()
# everywhere and makes the decorators cleaner.
# @app.before_request
# def load_logged_in_user():
#     g.user = session.get("username", None)
@app.before_request
def load_logged_in_user():
    username = session.get("username", None)
    if username:
        db = get_db()
        user = db.execute("""
                          SELECT *
                          FROM users
                          WHERE username = ?;
                          """, (username,)).fetchone()
        if user is None:
            session.clear()
            g.user = None
        else:
            g.user = user
    else:
        g.user = None

# Protects routes that require a user to be logged in.
def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("login", next=request.url))
        return view(*args, **kwargs)
    return wrapped_view

# This function will make it easier to send push notifications.
# It looks up the username provided and finds all FCM tokens associated
# with that user (they might have multiple tokens if they're logged in on different
# devices or browsers) and sends the notification to each one.
# Example:
# send_notification("Sean", "Reminder", "Take your medication.")
def send_notification(username, title, body):
    db = get_db()
    user = db.execute("""
                        SELECT *
                        FROM users
                        WHERE username = ?;
                        """, (username,)).fetchone()
    if user:
        user_id = user["user_id"]
        fcm_tokens = db.execute("""
                        SELECT token
                        FROM fcm_tokens
                        WHERE user_id = ?;
                        """, (user_id,)).fetchall()
        fcm_tokens = [row["token"] for row in fcm_tokens]
        for fcm_token in fcm_tokens:
            try:
                message = messaging.Message(
                    notification=messaging.Notification(
                        title=title,
                        body=body
                    ),
                    token=fcm_token
                )
                messaging.send(message)
            except Exception as e:
                # If Firebase says the token is no longer valid
                # this removes it from the database so we don't keep
                # retrying it
                if "registration-token-not-registered" in str(e):
                    db.execute("""
                               DELETE FROM fcm_tokens
                               WHERE token = ?;
                               """, (fcm_token,))
                    db.commit()
                print(f"Error: {e}")

# This function checks every minute which medications are due
def reminder_scheduler():
    with app.app_context():
        # current_time = datetime.now()
        current_time_utc = datetime.now(timezone.utc)
        db = get_db()
        # Get all medications for today
        medications = db.execute(""" 
                                SELECT m.user_medication_id, m.user_id, u.username, m.medication_name, m.dosage_amount, m.dosage_unit, mt.time_of_day, u.timezone
                                FROM medications m JOIN medication_times mt ON m.user_medication_id = mt.user_medication_id
                                JOIN users u ON m.user_id = u.user_id
                                WHERE m.push_notifications_enabled = 1 AND m.start_date <= ? AND (m.end_date IS NULL OR m.end_date >= ?);
                                """, (current_time_utc.date(), current_time_utc.date())).fetchall()
        for medication in medications:
            # Convert the current UTC time into the user's local timezone
            user_time_zone = pytz.timezone(medication["timezone"]) if medication["timezone"] else pytz.utc
            user_current_time = current_time_utc.astimezone(user_time_zone)
            if medication["time_of_day"] == user_current_time.strftime("%H:%M"):
                # Check if the reminder was already sent today (we want to avoid duplicates)
                reminder_sent = db.execute("""
                                        SELECT 1
                                        FROM medication_reminders_sent
                                        WHERE user_medication_id = ? AND time_of_day = ? AND date_sent = ?;
                                        """, (medication["user_medication_id"], medication["time_of_day"], user_current_time.date())).fetchone()
                # Skip it if it was already sent
                if reminder_sent:
                    continue
                username = medication["username"]
                send_notification(
                    username=username,
                    title="Medication Reminder",
                    body=f"{medication['dosage_amount']} {medication['dosage_unit']} of {medication['medication_name']} is due."
                )
                # Record that the notification was sent
                db.execute("""
                        INSERT OR IGNORE INTO medication_reminders_sent (user_medication_id, time_of_day, date_sent)
                        VALUES (?, ?, ?);
                        """, (medication["user_medication_id"], medication["time_of_day"], user_current_time.date()))
                db.commit()
scheduler = BackgroundScheduler()
scheduler.add_job(reminder_scheduler, "interval", minutes=1)
scheduler.start()
   
# This is the home page route.
@app.route("/")
def index():
    return render_template("index.html", title="Home")

@app.route("/set_timezone", methods=["POST"])
@login_required
def set_timezone():
    timezone = request.json.get("timezone")
    if timezone:
        db = get_db()
        username = session["username"]
        db.execute("""
                   UPDATE users
                   SET timezone = ?
                   WHERE username = ?;
                   """, (timezone, username))
        db.commit()
    # Returns 204 No Content
    return "", 204

# This route shows a small preview of what notifications
# will look like if anyone wants to see. We'll delete this
# later.
@app.route("/test_notification", methods=["GET", "POST"])
@login_required
def test_notification():
    send_notification(
        username=session["username"],
        title="Test",
        body="This is a test"
    )
    return render_template("test_notification.html", title="Test Notification")

# This is called if the user gives notification permission and Firebase
# generates a token. The token is stored in the database so we can
# later send push notifications to the user. A user can have multiple
# tokens (e.g. if they are logged in on different browsers/devices).
@app.route("/save_token", methods=["POST"])
@login_required
def save_token():
    token = request.get_json().get("token")
    username = session["username"]
    if token and username:
        db = get_db()
        user = db.execute("""
                          SELECT *
                          FROM users
                          WHERE username = ?;
                          """, (username,)).fetchone()
        if user:
            user_id = user["user_id"]
            db.execute("""
                       INSERT OR IGNORE INTO fcm_tokens (user_id, token)
                       VALUES
                       (?, ?);
                       """, (user_id, token))
            db.commit()
            return jsonify({"success": True, "token": token})
    return jsonify({"success": False, "error": "Something went wrong"})

# This is the registration route. It displays the registration form,
# validates the input, checks if the provided username already exists, 
# hashes the password before storing it in the database and redirects 
# the user to the login page if the registration was successful.
@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        email = form.email.data
        username = form.username.data
        password = form.password.data
        db = get_db()
        existing_user = db.execute("""
                                SELECT *
                                FROM users
                                WHERE email = ? OR username = ?;
                                """, (email, username)).fetchone()
        if existing_user is not None:
            if existing_user["email"] == email:
                form.email.errors.append("This email is already in use.")
            if existing_user["username"] == username:
                form.username.errors.append("This username is already taken.")
        else:
            db.execute("""
                       INSERT INTO users (email, username, password)
                       VALUES
                       (?, ?, ?);
                       """, (email, username, generate_password_hash(password)))
            db.commit()
            return redirect( url_for("login") )
    return render_template("register.html", title="Register", form=form)

# This is the login route. It displays the login form, checks
# the input against the database including the hashed password, sets
# the session to keep the user logged in and redirects them to the original
# page if "next" is provided.
@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        identifier = form.identifier.data # Changed the variable name to identifier as the user may enter their email or username
        password = form.password.data
        db = get_db()
        existing_user = db.execute("""
                                SELECT *
                                FROM users
                                WHERE username = ? OR email = ?;
                                """, (identifier, identifier)).fetchone()
        # Changed error message to be generic to prevent against enumeration attacks
        if (existing_user is None) or (not check_password_hash(existing_user["password"], password)):
            form.identifier.errors.append("The information you have provided is incorrect.")
        else:
            session.clear()
            session["username"] = existing_user["username"]
            session.permanent = form.remember.data # This line makes "Remember Me?" work
            next_page = request.args.get("next")
            if not next_page:
                next_page = url_for("index")
            return redirect(next_page)
    return render_template("login.html", title="Login", form=form)

@app.route("/logout")
def logout():
    session.clear()
    return redirect( url_for("index") )

@app.route("/add_medication", methods=["GET", "POST"])
@login_required
def add_medication():
    form = AddMedicationForm()
    if form.validate_on_submit():
        username = session["username"]
        medication_name = form.medication_name.data
        dosage_amount = float(form.dosage_amount.data)
        dosage_unit = form.dosage_unit.data
        frequency_count = form.frequency_count.data
        frequency_type = form.frequency_type.data
        time_of_day = form.time_of_day.data
        start_date = form.start_date.data
        end_date = form.end_date.data
        instructions = form.instructions.data
        push_notifications_enabled = int(form.push_notifications_enabled.data)
        has_errors = False
        # For validating the dates
        if (end_date) and (end_date < start_date):
            form.end_date.errors.append("The end date cannot be before the start date.")
            has_errors = True
        # For validating the number of time entries provided.
        times = [time for time in time_of_day if time is not None]
        if frequency_type != "as_needed":
            if len(times) != frequency_count:
                form.time_of_day.errors.append(f"Please enter exactly {frequency_count} time(s).")
                has_errors = True
        if not has_errors:
            db = get_db()
            user = db.execute("""
                            SELECT user_id
                            FROM users
                            WHERE username = ?;
                            """, (username,)).fetchone()
            if user:
                user_id = user["user_id"]
                cursor = db.execute("""
                        INSERT INTO medications (user_id, medication_name, dosage_amount, dosage_unit, frequency_count, frequency_type, start_date, end_date, instructions, push_notifications_enabled)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """, (user_id, medication_name, dosage_amount, dosage_unit, frequency_count, frequency_type, start_date, end_date, instructions, push_notifications_enabled))
                user_medication_id = cursor.lastrowid
                for time in times:
                    db.execute("""
                            INSERT INTO medication_times (user_medication_id, time_of_day)
                            VALUES (?, ?);
                            """, (user_medication_id, time.strftime("%H:%M")))
                db.commit()
                return redirect( url_for("history") )
    return render_template("add_medication.html", title="Add Medication", form=form)

@app.route("/history")
@login_required
def history():
    db = get_db()
    username = session["username"]
    user = db.execute("""
                    SELECT user_id FROM users WHERE username = ?;
                    """, (username,),).fetchone()
    medications = []
    if user:
        user_id = user["user_id"]
        medications = db.execute("""
                                SELECT *
                                FROM medications
                                WHERE user_id = ?
                                ORDER BY start_date DESC;
                                """, (user_id,),).fetchall()
    return render_template("history.html", title="Medication History", medications=medications)

@app.route("/add_mate", methods=["GET", "POST"])
@login_required
def add_mate():
    response = ""
    form = AddMateForm()
    if form.validate_on_submit():
        sender = session["username"]
        receiver = form.username.data
        if sender == receiver:
            form.username.errors.append("You Cannot invite yourself.")
            return render_template("add_mate.html", title="Add Mates", form=form, response=response)
        db = get_db()
        existing_user = db.execute("""
                                SELECT *
                                FROM users
                                WHERE username = ?;
                                """, (receiver,)).fetchone()
        
        existing_invite = db.execute("""
                                     SELECT *
                                     FROM invites
                                     WHERE sender = ? AND receiver = ?;
                                     """, (sender, receiver,)).fetchone()
        if existing_invite is not None:
            form.username.errors.append("You have already sent this user an invite.")
        elif existing_user is not None:
            db.execute("""
                       INSERT INTO invites (sender, receiver)
                       VALUES
                       (?, ?);
                       """, (sender, receiver,))
            db.commit()
            response = "Mate Request Sent"
        else:
            form.username.errors.append("This user does not exist.")
    return render_template("add_mate.html", title="Add Mates", form=form, response=response)

@app.route("/pending_requests")
@login_required
def pending_requests():
    sender = session["username"]
    db = get_db()
    invites = db.execute("""
                    SELECT *
                    FROM invites
                    WHERE sender = ?""", (sender,))
    return render_template("pending_requests.html", title="Add Mates", invites=invites)

@app.route("/mate_requests")
@login_required
def mate_requests():
    user = session["username"]
    db = get_db()
    invites = db.execute("""
                    SELECT *
                    FROM invites
                    WHERE receiver = ?""", (user,))
    return render_template("mate_requests.html", title="Add Mates", invites=invites)
    

@app.route("/cancel_request/<string:receiver>")
@login_required
def cancel_request(receiver):
    sender = session["username"]
    db = get_db()
    db.execute(
        '''DELETE FROM invites
        WHERE sender = ? AND receiver = ?;''', (sender, receiver,))
    db.commit()
    invites = db.execute("""
                            SELECT *
                            FROM invites
                            WHERE sender = ?""", (sender,))
    return render_template("pending_requests.html", title="Pending Requests", invites=invites)


@app.route("/accept_request/<string:friend1>")
@login_required
def accept_request(friend1):
    friend2 = session["username"]
    db = get_db()
    db.execute("""
                INSERT INTO friends (friend1, friend2)
                VALUES
                (?, ?);
                """, (friend1, friend2,))
    db.commit()
    db.execute(
        '''DELETE FROM invites
        WHERE sender = ? AND receiver = ?;''', (friend1, friend2,))
    db.commit()
    invites = db.execute("""
                            SELECT *
                            FROM invites
                            WHERE receiver = ?""", (friend2,))
    return render_template("mate_requests.html", title="Mate Requests", invites=invites)
        
@app.route("/reject_request/<string:sender>")
@login_required
def reject_request(sender):
    user = session["username"]
    db = get_db()
    db.execute(
        '''DELETE FROM invites
        WHERE sender = ? AND receiver = ?;''', (sender, user,))
    db.commit()
    invites = db.execute("""
                            SELECT *
                            FROM invites
                            WHERE sender = ?""", (sender,))
    return render_template("mate_requests.html", title="Mate Requests", invites=invites)

@app.route("/symptom", methods=["GET", "POST"])
@login_required
def symptom():
    form = SymptomForm()
    db = get_db()
    user = db.execute(
        "SELECT user_id FROM users WHERE username = ?",
        (session["username"],),
    ).fetchone()
    if form.validate_on_submit():
        db.execute(
            """
            INSERT INTO symptoms (
                user_id,
                symptom_name,
                severity,
                symptom_date,
                symptom_time,
                medication_name,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user["user_id"],
                form.symptom_name.data,
                int(form.severity.data),
                form.symptom_date.data,
                form.symptom_time.data,
                form.medication_name.data,
                form.notes.data,
            ),
        )
        db.commit()
        return redirect(url_for("symptom"))
    symptoms = db.execute(
        """
        SELECT *
        FROM symptoms
        WHERE user_id = ?
        ORDER BY symptom_date DESC
        """,
        (user["user_id"],),
    ).fetchall()
    return render_template(
        "symptom.html",
        form=form,
        symptoms=symptoms
    )

if __name__ == "__main__":
    app.run(debug=True)