#!/usr/bin/env python3
from flask import Flask, render_template, redirect, url_for, session, g, request, jsonify
# Server-side session management
from flask_session import Session
from forms import RegistrationForm, LoginForm, AddMedicationForm
from database import get_db, close_db
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import timedelta

app = Flask(__name__)
# Secret key for signing sessions to protect against CSRF attacks.
app.config["SECRET_KEY"] = "this-is-my-secret-key"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"

app.permanent_session_lifetime = timedelta(days=30) # makes the lifetime of remember me to be 30 days

# These are needed to send push notifications
import firebase_admin
from firebase_admin import credentials, messaging
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

Session(app)

# Ensures the database connection is closed after each request.
app.teardown_appcontext(close_db)

# This will run before every request. It avoids repeating session.get()
# everywhere and makes the decorators cleaner.
@app.before_request
def load_logged_in_user():
    g.user = session.get("username", None)

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
                    db.execute(
                        """DELETE FROM fcm_tokens
                        WHERE token = ?;
                        """, (fcm_token,)
                    )
                    db.commit()
                print(f"Error: {e}")

# This is the home page route.
@app.route("/")
def index():
    return render_template("index.html", title="Home")

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
        username = form.username.data
        password = form.password.data
        db = get_db()
        existing_user = db.execute("""
                                SELECT *
                                FROM users
                                WHERE username = ?;
                                """, (username,)).fetchone()
        if existing_user is not None:
            form.username.errors.append("This username is already taken.")
        else:
            db.execute("""
                       INSERT INTO users (username, password)
                       VALUES
                       (?, ?);
                       """, (username, generate_password_hash(password)))
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
        username = form.username.data
        password = form.password.data
        db = get_db()
        existing_user = db.execute("""
                                SELECT *
                                FROM users
                                WHERE username = ?;
                                """, (username,)).fetchone()
        if existing_user is None:
            form.username.errors.append("This username does not exist.")
        elif not check_password_hash(existing_user["password"], password):
            form.password.errors.append("The password you have provided is incorrect.")
        else:
            session.clear()
            session["username"] = username
            session.permanent = form.remember.data #this line makes "remember me" work
            next_page = request.args.get("next")
            if not next_page:
                next_page = url_for("index")
            return redirect(next_page)
    return render_template("login.html", title="Login", form=form)

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
        reminders_enabled = int(form.reminders_enabled.data)
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
                        INSERT INTO medications (user_id, medication_name, dosage_amount, dosage_unit, frequency_count, frequency_type, start_date, end_date, instructions, reminders_enabled)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """, (user_id, medication_name, dosage_amount, dosage_unit, frequency_count, frequency_type, start_date, end_date, instructions, reminders_enabled))
                user_medication_id = cursor.lastrowid
                for time in times:
                    db.execute("""
                            INSERT INTO medication_times (user_medication_id, time_of_day)
                            VALUES (?, ?);
                            """, (user_medication_id, time.strftime("%H:%M")))
                db.commit()
                return redirect( url_for("history") )
    return render_template("add_medication.html", title="Add Medication", form=form)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/history")
@login_required
def history():
    db = get_db()

    user = db.execute(
        "SELECT user_id FROM users WHERE username = ?",
        (session["username"],),
    ).fetchone()

    medications = db.execute(
        """
        SELECT *
        FROM medications
        WHERE user_id = ?
        ORDER BY start_date DESC;
        """,
        (user["user_id"],),
    ).fetchall()

    return render_template(
        "history.html",
        title="Medication History",
        medications=medications
    )


if __name__ == "__main__":
    app.run(debug=True)