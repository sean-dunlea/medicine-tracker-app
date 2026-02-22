#!/usr/bin/env python3
from flask import Flask, render_template, redirect, url_for, session, g, request, jsonify, flash
# Server-side session management
from flask_session import Session
from forms import RegistrationForm, LoginForm, AddMedicationForm, AddMateForm, LogSymptomForm, ChangeEmailForm, ChangePasswordForm, PreferencesForm
from database import get_db, close_db, initialise_drugbank
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import date, timedelta
import os

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

# These are needed to send email notifications
from flask_mailman import Mail, EmailMessage
from dotenv import load_dotenv
load_dotenv()
username = os.environ.get("MAIL_USERNAME")
password = os.environ.get("MAIL_PASSWORD")
app.config.update(
    MAIL_SERVER="smtp.gmail.com",
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME=username,
    MAIL_PASSWORD=password,
    MAIL_DEFAULT_SENDER=os.environ.get("MAIL_USERNAME").strip()
)
mail = Mail(app)

Session(app)

# Ensures the database connection is closed after each request.
app.teardown_appcontext(close_db)
# This initialises the DrugBank database
initialise_drugbank()

# This will run before every request. It avoids repeating session.get()
# everywhere and makes the decorators cleaner.
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
# send_push_notification("Sean", "Reminder", "Take your medication.")
def send_push_notification(username, title, body):
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

# This function will make it easier to send email notifications.
# Example:
# send_email_notification("Sean", "Reminder", "Take your medication.")
def send_email_notification(username, title, body):
    db = get_db()
    user = db.execute("""
                        SELECT *
                        FROM users
                        WHERE username = ?;
                        """, (username,)).fetchone()
    if user:
        recipient = user["email"]
        message = EmailMessage(
            subject=title,
            body=body,
            to=[recipient]
        )
        try:
            message.send()
        except Exception as e:
            print(f"Error sending email to {recipient}: {e}")

# This function checks every minute which medications are due
def reminder_scheduler():
    with app.app_context():
        current_time_utc = datetime.now(timezone.utc)
        db = get_db()
        # Get all medications for today
        medications = db.execute(""" 
                                SELECT m.user_medication_id, m.user_id, u.username, u.email, m.medication_name, m.dosage_amount, m.dosage_unit, m.frequency_type, mt.time_of_day, u.timezone, m.push_notifications_enabled, m.email_notifications_enabled, mt.weekday, mt.day_of_month
                                FROM medications m JOIN medication_times mt ON m.user_medication_id = mt.user_medication_id
                                JOIN users u ON m.user_id = u.user_id
                                WHERE m.start_date <= ? AND (m.end_date IS NULL OR m.end_date >= ?);
                                """, (current_time_utc.date(), current_time_utc.date())).fetchall()
        for medication in medications:
            # Convert the current UTC time into the user's local timezone
            user_time_zone = pytz.timezone(medication["timezone"]) if medication["timezone"] else pytz.utc
            user_current_time = current_time_utc.astimezone(user_time_zone)
            current_weekday = user_current_time.weekday()
            current_day_of_month = user_current_time.day
            frequency_type = medication["frequency_type"]
            if frequency_type == "weekly":
                if medication["weekday"] != current_weekday:
                    continue
            if frequency_type == "monthly":
                if medication["day_of_month"] != current_day_of_month:
                    continue
            if frequency_type == "as_needed":
                continue
            # This converts the stored medication time to a time object and strips the seconds and milliseconds
            medication_time = datetime.strptime(medication["time_of_day"], "%H:%M").time()
            # This compares only the hours and minutes (ignores seconds and microseconds) to avoid small mismatches
            if medication_time != user_current_time.time().replace(second=0, microsecond=0):
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
                notification_sent = False
                if medication["push_notifications_enabled"]:
                    send_push_notification(
                        username=username,
                        title="Medication Reminder 💊",
                        body=f"Hey, {username}! It's time for {medication['dosage_amount']} {medication['dosage_unit']} of {medication['medication_name']}. Keep up the great work!"
                    )
                    notification_sent = True
                if medication["email_notifications_enabled"] and medication["email"]:
                    send_email_notification(
                        username=username,
                        title="Medication Reminder 💊",
                        body=f"Hello, {username},\n\nThis is a friendly reminder that it's time for {medication['dosage_amount']} {medication['dosage_unit']} of {medication['medication_name']}.\n\nStay healthy and keep up the great work!"
                    )
                    notification_sent = True
                # Record that the notification was sent
                if notification_sent:
                    db.execute("""
                            INSERT OR IGNORE INTO medication_reminders_sent (user_medication_id, time_of_day, date_sent)
                            VALUES (?, ?, ?);
                            """, (medication["user_medication_id"], medication["time_of_day"], user_current_time.date()))
                    db.commit()
scheduler = BackgroundScheduler()
scheduler.add_job(reminder_scheduler, "interval", minutes=1, replace_existing=True)
scheduler.start()

@app.route("/calendar")
@login_required
def calendar():
    calendar_year = build_year_calendar(g.user["user_id"])
    return render_template("calendar.html", calendar=calendar_year)

def build_week_calendar(user_id):
    # This calculates the current week from Monday to Sunday
    today = date.today()
    # This gets the first day of the week by subtracting the current weekday index
    monday = today - timedelta(days=today.weekday())
    # This generates the list of 7 days
    weekdays = [monday + timedelta(days=weekday_index) for weekday_index in range(7)]
    # This gets the user's medications and the times
    db = get_db()
    medications = db.execute(""" 
                             SELECT m.user_medication_id, m.medication_name, m.frequency_type, m.start_date, m.end_date, mt.time_of_day, mt.weekday
                             FROM medications m JOIN medication_times mt ON m.user_medication_id = mt.user_medication_id
                             WHERE m.user_id = ?;
                             """, (user_id,)).fetchall()
    # This gets the medication logs for this week
    medication_logs = db.execute("""
                                 SELECT user_medication_id, scheduled_date, time_of_day
                                 FROM medication_logs
                                 WHERE user_medication_id IN (SELECT user_medication_id FROM medications WHERE user_id = ?)
                                 AND scheduled_date BETWEEN ? AND ?
                                 """, (user_id, monday, monday + timedelta(days=6))).fetchall()
    # This builds a dictionary to check if a medication was taken on a specific day
    medication_log_dict = {(medication_log["user_medication_id"], medication_log["scheduled_date"], medication_log["time_of_day"]): True for medication_log in medication_logs}
    # This prepares the calendar
    calendar = {weekday: [] for weekday in weekdays}
    for weekday in weekdays:
        for medication in medications:
            # This ignores medications that haven't started yet or ones that already ended
            if weekday < medication["start_date"]:
                continue
            if medication["end_date"] and weekday > medication["end_date"]:
                continue
            include = False
            if medication["frequency_type"] == "daily":
                include = True
            elif medication["frequency_type"] == "weekly":
                if medication["weekday"] == weekday.weekday():
                    include = True
            if include:
                already_taken = medication_log_dict.get((medication["user_medication_id"], weekday, medication["time_of_day"]), False)
                medication_datetime = datetime.combine(weekday, datetime.strptime(medication["time_of_day"], "%H:%M").time())
                can_take = datetime.now() >= medication_datetime
                if already_taken:
                    can_take = False
                else:
                    can_take = datetime.now() >= medication_datetime
                calendar[weekday].append({
                    "user_medication_id": medication["user_medication_id"],
                    "medication_name": medication["medication_name"],
                    "time_of_day": medication["time_of_day"],
                    "taken": already_taken,
                    "can_take": can_take
                })
    return calendar

def build_year_calendar(user_id):
    db = get_db()
    today = date.today()
    start_of_year = date(today.year, 1, 1)
    end_of_year = date(today.year, 12, 31)
    total_days = (end_of_year - start_of_year).days + 1
    days = [start_of_year + timedelta(days=i) for i in range(total_days)]
    medications = db.execute("""
        SELECT m.user_medication_id, m.medication_name,
               m.frequency_type, m.start_date, m.end_date,
               mt.time_of_day, mt.weekday
        FROM medications m
        JOIN medication_times mt
        ON m.user_medication_id = mt.user_medication_id
        WHERE m.user_id = ?
    """, (user_id,)).fetchall()

    medication_logs = db.execute("""
        SELECT user_medication_id, scheduled_date, time_of_day
        FROM medication_logs
        WHERE user_medication_id IN (
            SELECT user_medication_id FROM medications WHERE user_id = ?
        )
    """, (user_id,)).fetchall()
    log_dict = {
        (log["user_medication_id"], log["scheduled_date"], log["time_of_day"]): True
        for log in medication_logs
    }
    calendar = {day: [] for day in days}
    for day in days:
        for medication in medications:
            if day < medication["start_date"]:
                continue
            if medication["end_date"] and day > medication["end_date"]:
                continue
            include = False
            if medication["frequency_type"] == "daily":
                include = True
            elif medication["frequency_type"] == "weekly":
                if medication["weekday"] == day.weekday():
                    include = True
            if include:
                taken = log_dict.get(
                    (medication["user_medication_id"], day, medication["time_of_day"]),
                    False
                )
                calendar[day].append({
                    "medication_name": medication["medication_name"],
                    "time_of_day": medication["time_of_day"],
                    "taken": taken
                })
    return calendar

# This is the home page route.
@app.route("/")
def index():
    if not g.user:
        return render_template("index.html", title="Home")
    calendar = build_week_calendar(g.user["user_id"])
    return render_template("index.html", title="Home", calendar=calendar)

@app.route("/week_calendar")
@login_required
def week_calendar():
    calendar = build_week_calendar(g.user["user_id"])
    return render_template("week_calendar.html", calendar=calendar)

@app.route("/log_medication/<int:user_medication_id>", methods=["POST"])
@login_required
def log_medication(user_medication_id):
    db = get_db()
    scheduled_date = request.form.get("scheduled_date")
    time_of_day = request.form.get("time_of_day")
    existing_log = db.execute("""
                              SELECT 1
                              FROM medication_logs
                              WHERE user_medication_id = ? AND scheduled_date = ? AND time_of_day = ?
                              """, (user_medication_id, scheduled_date, time_of_day)).fetchone()
    if not existing_log:
        db.execute("""
                INSERT OR IGNORE INTO medication_logs (user_medication_id, scheduled_date, time_of_day)
                VALUES (?, ?, ?);
                """, (user_medication_id, scheduled_date, time_of_day))
        db.commit()
    return redirect( url_for("week_calendar") )

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
@app.route("/test_push_notification", methods=["GET", "POST"])
@login_required
def test_push_notification():
    send_push_notification(
        username=session["username"],
        title="Test",
        body="This is a test"
    )
    return render_template("test_push_notification.html", title="Test Push Notification")

@app.route("/test_email_notification", methods=["GET", "POST"])
@login_required
def test_email_notification():
    send_email_notification(
        username=session["username"],
        title="Test",
        body="This is a test"
    )
    return render_template("test_email_notification.html", title="Test Email Notification")

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
    login_form = LoginForm()
    registration_form = RegistrationForm()
    if registration_form.validate_on_submit():
        email = registration_form.email.data
        username = registration_form.username.data
        password = registration_form.password.data
        db = get_db()
        existing_user = db.execute("""
                                SELECT *
                                FROM users
                                WHERE email = ? OR username = ?;
                                """, (email, username)).fetchone()
        if existing_user is not None:
            if existing_user["email"] == email:
                registration_form.email.errors.append("This email is already in use.")
            if existing_user["username"] == username:
                registration_form.username.errors.append("This username is already taken.")
        else:
            db.execute("""
                       INSERT INTO users (email, username, password)
                       VALUES
                       (?, ?, ?);
                       """, (email, username, generate_password_hash(password)))
            db.commit()
            return redirect( url_for("login") )
    return render_template("auth.html", title="Register", login_form=login_form, registration_form=registration_form)

# This is the login route. It displays the login form, checks
# the input against the database including the hashed password, sets
# the session to keep the user logged in and redirects them to the original
# page if "next" is provided.
@app.route("/login", methods=["GET", "POST"])
def login():
    login_form = LoginForm()
    registration_form = RegistrationForm()
    if login_form.validate_on_submit():
        identifier = login_form.identifier.data # Changed the variable name to identifier as the user may enter their email or username
        password = login_form.password.data
        db = get_db()
        existing_user = db.execute("""
                                SELECT *
                                FROM users
                                WHERE username = ? OR email = ?;
                                """, (identifier, identifier)).fetchone()
        # Changed error message to be generic to prevent against enumeration attacks
        if (existing_user is None) or (not check_password_hash(existing_user["password"], password)):
            login_form.identifier.errors.append("The information you have provided is incorrect.")
        else:
            session.clear()
            session["username"] = existing_user["username"]
            session.permanent = login_form.remember.data # This line makes "Remember Me?" work
            next_page = request.args.get("next")
            if not next_page:
                next_page = url_for("index")
            return redirect(next_page)
    return render_template("auth.html", title="Login", login_form=login_form, registration_form=registration_form)

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
        time_entries = form.time_entries.data
        start_date = form.start_date.data
        end_date = form.end_date.data
        instructions = form.instructions.data
        push_notifications_enabled = int(form.push_notifications_enabled.data)
        email_notifications_enabled = int(form.email_notifications_enabled.data)
        has_errors = False
        # For validating the dates
        if (end_date) and (end_date < start_date):
            form.end_date.errors.append("The end date cannot be before the start date.")
            has_errors = True
        # For validating the number of time entries provided.
        valid_time_entries = [time_entry for time_entry in time_entries if time_entry["time_of_day"]]
        if frequency_type != "as_needed":
            if len(valid_time_entries) != frequency_count:
                form.time_entries.errors.append(f"Please enter exactly {frequency_count} time(s).")
                has_errors = True
        if frequency_type == "weekly":
            for entry in valid_time_entries:
                if not entry["weekday"]:
                    form.time_entries.errors.append("Please select a weekday for each time.")
                    has_errors = True
                    break
        if frequency_type == "monthly":
            for entry in valid_time_entries:
                if not entry["day_of_month"]:
                    form.time_entries.errors.append("Please enter a day of month for each time.")
                    has_errors = True
                    break
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
                        INSERT INTO medications (user_id, medication_name, dosage_amount, dosage_unit, frequency_count, frequency_type, start_date, end_date, instructions, push_notifications_enabled, email_notifications_enabled)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """, (user_id, medication_name, dosage_amount, dosage_unit, frequency_count, frequency_type, start_date, end_date, instructions, push_notifications_enabled, email_notifications_enabled))
                user_medication_id = cursor.lastrowid
                for entry in valid_time_entries:
                    time_value = entry["time_of_day"].strftime("%H:%M")
                    weekday = entry["weekday"]
                    day_of_month = entry["day_of_month"]
                    weekday = int(weekday) if weekday else None
                    day_of_month = int(day_of_month) if day_of_month else None
                    db.execute("""
                               INSERT INTO medication_times (user_medication_id, time_of_day, weekday, day_of_month)
                               VALUES (?, ?, ?, ?);
                               """, (user_medication_id, time_value, weekday, day_of_month))
                db.commit()
                return redirect( url_for("history") )
    return render_template("add_medication.html", title="Add Medication", form=form)

@app.route("/query_medications", methods=["GET"])
def query_medications():
    medication_query = request.args.get("q", "")
    if len(medication_query) >= 2:
        db = get_db()
        # These results are more user-friendly and human-readable (brands and synonyms)
        cursor = db.execute("""
                            SELECT DISTINCT name
                            FROM drugbank_products
                            WHERE name LIKE ?
                            ORDER BY LENGTH(name) ASC
                            LIMIT 10
                            """, (f"{medication_query}%",))
        results = [{"name": row["name"]} for row in cursor.fetchall()]
        # If it returns less than 10 results, we'll use these as well (generic names)
        if len(results) < 10:
            cursor = db.execute("""
                                SELECT DISTINCT generic_name AS name 
                                FROM drugbank_drugs
                                WHERE generic_name LIKE ?
                                ORDER BY LENGTH(generic_name) ASC
                                LIMIT ?
                                """, (f"{medication_query}%", 10 - len(results)))
        results += [{"name": row["name"]} for row in cursor.fetchall()]
        return jsonify(results)
    return jsonify([])

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

#@app.route("/add_mate", methods=["GET", "POST"])
#@login_required
#def add_mate():
#    response = ""
#    form = AddMateForm()
#    if form.validate_on_submit():
#        sender = session["username"]
#        receiver = form.username.data
#        if sender == receiver:
#            form.username.errors.append("You cannot invite yourself.")
#            return render_template("add_mate.html", title="Add Mates", form=form, response=response)
#        db = get_db()
#        existing_user = db.execute("""
#                                SELECT *
#                                FROM users
#                                WHERE username = ?;
#                                """, (receiver,)).fetchone()
#        
#        existing_invite = db.execute("""
#                                     SELECT *
#                                     FROM invites
#                                     WHERE sender = ? AND receiver = ?;
#                                     """, (sender, receiver,)).fetchone()
#        if existing_invite is not None:
#            form.username.errors.append("You have already sent this user an invite.")
#        elif existing_user is not None:
#            db.execute("""
#                       INSERT INTO invites (sender, receiver)
#                       VALUES
#                       (?, ?);
#                       """, (sender, receiver,))
#            db.commit()
#            response = "Mate Request Sent"
#            title = "New Mate Request! 💊"
#            body = f"{sender} has sent you a MediMate request!"
#            send_email_notification(receiver, title, body)
#            send_push_notification(receiver, title, body)
#        else:
#            form.username.errors.append("This user does not exist.")
#    return render_template("add_mate.html", title="Add Mates", form=form, response=response)
    
@app.route("/cancel_request/<string:receiver>")
@login_required
def cancel_request(receiver):
    sender = session["username"]
    db = get_db()
    db.execute("""
               DELETE FROM invites
               WHERE sender = ? AND receiver = ?;
               """, (sender, receiver,))
    db.commit()
    invites = db.execute("""
                         SELECT *
                         FROM invites
                         WHERE sender = ?
                         """, (sender,))
    return redirect(url_for("medimates"))

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
    
    db.execute("""
                INSERT INTO friends (friend1, friend2)
                VALUES
                (?, ?);
                """, (friend2, friend1,))

    db.execute("""
               DELETE FROM invites
               WHERE sender = ? AND receiver = ?;
               """, (friend1, friend2,))
    db.commit()

    # This notifies the sender that their request was accepted yurrr
    title = "Mate Request Accepted! 💊"
    body = f"{friend2} has accepted your MediMate request!"
    send_email_notification(friend1, title, body)
    send_push_notification(friend1, title, body)

    invites = db.execute("""
                         SELECT *
                         FROM invites
                         WHERE receiver = ?
                         """, (friend2,))
    return redirect(url_for("medimates"))
        
@app.route("/reject_request/<string:sender>")
@login_required
def reject_request(sender):
    user = session["username"]
    db = get_db()
    db.execute("""
               DELETE FROM invites
               WHERE sender = ? AND receiver = ?;
               """, (sender, user,))
    db.commit()
    # This notifies the sender that the receiver was too cool for them :(
    title = "Mate Request Rejected"
    body = f"{user} has rejected your MediMate request."
    send_email_notification(sender, title, body)
    send_push_notification(sender, title, body)
    invites = db.execute("""
                         SELECT *
                         FROM invites
                         WHERE sender = ?
                         """, (sender,))
    return redirect(url_for("medimates"))

@app.route("/medimates", methods=["GET", "POST"])
@login_required
def medimates():
    response = ""
    db = get_db()
    user = session["username"]
    form = AddMateForm()
    if form.validate_on_submit():
        receiver = form.username.data
        if user == receiver:
            form.username.errors.append("You cannot invite yourself.")
            return render_template("add_mate.html", title="Add Mates", form=form, response=response)
        existing_user = db.execute("""
                                SELECT *
                                FROM users
                                WHERE username = ?;
                                """, (receiver,)).fetchone()
        
        existing_invite = db.execute("""
                                     SELECT *
                                     FROM invites
                                     WHERE sender = ? AND receiver = ?;
                                     """, (user, receiver,)).fetchone()
        if existing_invite is not None:
            form.username.errors.append("You have already sent this user an invite.")
        elif existing_user is not None:
            db.execute("""
                       INSERT INTO invites (sender, receiver)
                       VALUES
                       (?, ?);
                       """, (user, receiver,))
            db.commit()
            response = "Mate Request Sent"
            title = "New Mate Request! 💊"
            body = f"{user} has sent you a MediMate request!"
            send_email_notification(receiver, title, body)
            send_push_notification(receiver, title, body)
        else:
            form.username.errors.append("This user does not exist.")

    medimates = db.execute("""
                    SELECT *
                    FROM friends
                    WHERE friend1 = ?""", (user,))
    
    invites = db.execute("""
                    SELECT *
                    FROM invites
                    WHERE receiver = ?""", (user,))
    pending_requests = db.execute("""
                    SELECT *
                    FROM invites
                    WHERE sender = ?""", (user,))
    

    return render_template("medimates.html", title="Medimates", medimates=medimates, invites=invites, pending_requests=pending_requests, form=form, response=response)

@app.route("/remove_medimate/<string:friend>")
@login_required
def remove_medimate(friend):
    user = session["username"]
    db = get_db()
    db.execute("""
               DELETE FROM friends
               WHERE friend1 = ? AND friend2 = ?;
               """, (user, friend,))
    
    db.execute("""
               DELETE FROM friends
               WHERE friend1 = ? AND friend2 = ?;
               """, (friend, user,))
    
    db.commit()
    
    medimates = db.execute("""
                    SELECT *
                    FROM friends
                    WHERE friend1 = ?""", (user,))
    return redirect(url_for("medimates"))

    

#users can log their symptoms
@app.route("/log_symptom", methods=["GET", "POST"])
@login_required
def log_symptom():
    form = LogSymptomForm()
    db = get_db()
    user = db.execute("""
                      SELECT user_id 
                      FROM users 
                      WHERE username = ?
                      """, (session["username"],),).fetchone()
    if form.validate_on_submit():
        db.execute("""
                   INSERT INTO symptoms (user_id, symptom_name, severity, symptom_date, symptom_time, notes)
                   VALUES (?, ?, ?, ?, ?, ?)
                   """, (user["user_id"], form.symptom_name.data, int(form.severity.data), form.symptom_date.data,
                         form.symptom_time.data.strftime("%H:%M"), form.notes.data,),)
        db.commit()
        return redirect(url_for("log_symptom"))
    symptoms = db.execute("""
                          SELECT *
                          FROM symptoms
                          WHERE user_id = ?
                          ORDER BY symptom_date DESC
                          """,
        (user["user_id"],),).fetchall()
    return render_template("log_symptom.html", form=form, symptoms=symptoms)

#Users can print a report from their symptoms log to give to their gp/caretaker etc.
@app.route("/symptom/report")
@login_required
def symptom_report():
    db = get_db()
    user = db.execute("""
                      SELECT * 
                      FROM users 
                      WHERE username = ?
                      """, (session["username"],)).fetchone()
    symptoms = db.execute("""
                          SELECT *
                          FROM symptoms
                          WHERE user_id = ?
                          ORDER BY symptom_date DESC
                          """, (user["user_id"],)).fetchall()
    total_symptoms = len(symptoms)
    return render_template("symptom_report.html", user=user, symptoms=symptoms, total_symptoms=total_symptoms, generated_on=datetime.now())

#Profile section showing amount of mates 
@app.route("/profile")
@login_required
def profile():
    db = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE username = ?",
        (session["username"],),
    ).fetchone()

    mates = db.execute(
        """
        SELECT COUNT(*) FROM friends
        WHERE friend1 =? OR friend2 = ?
        """,
        (session["username"], session["username"]),
    ).fetchone()[0]
    return render_template("profile.html", user=user, mates=mates)

#Profile picture
@app.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    db = get_db()

    user = db.execute(
        "SELECT * FROM users WHERE username = ?",
        (session["username"],)
    ).fetchone()
    avatars = ["avatar1.png", "avatar2.png", "avatar3.png", "avatar4.png"]
    if request.method == "POST":
        selected_avatar = request.form.get("avatar")
        if selected_avatar in avatars:
            db.execute(
                "UPDATE users SET profile_picture = ? WHERE user_id = ?",
                (selected_avatar, user["user_id"]),
            )
            db.commit()
        return redirect(url_for("profile"))
    return render_template("edit_profile.html", user=user, avatars=avatars)

#Settings includes privacy feature allowing the user to show their activity to their mates, and also change their email and password
@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    db = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE username = ?",
        (session["username"],)
    ).fetchone()
    email_form = ChangeEmailForm(prefix="email")
    password_form = ChangePasswordForm(prefix="password")
    preferences_form = PreferencesForm(prefix="prefs")
    if request.method == "GET":
        email_form.email.data = user["email"]
        preferences_form.allow_mates_activity.data = bool(user["allow_mates_activity"])
    if email_form.submit.data and email_form.validate_on_submit():
        db.execute(
            "UPDATE users SET email = ? WHERE user_id = ?",
            (email_form.email.data, user["user_id"]),
        )
        db.commit()
        flash("Email updated successfully")
        return redirect(url_for("settings"))
    
    if password_form.submit.data and password_form.validate_on_submit():
        if not check_password_hash(user["password"], password_form.current_password.data):
            password_form.current_password.errors.append("Incorrect current password")
        else:
            new_hash = generate_password_hash(password_form.new_password.data)
            db.execute(
                "UPDATE users SET password = ? WHERE user_id = ?",
                (new_hash, user["user_id"]),
            )
            db.commit()
            flash("Password changed successfully")
            return redirect(url_for("settings"))
    return render_template(
        "settings.html",
        email_form=email_form,
        password_form=password_form,
        preferences_form=preferences_form,
        user=user,
    )
if __name__ == "__main__":
    app.run(debug=True)