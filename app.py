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
import calendar as pycalendar

# This is used to avoid sending duplicate notifications later
from sqlite3 import IntegrityError

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

# This is needed to generate AI-powered personalised health insights
import requests
OPEN_ROUTER_API_KEY = os.environ.get("OPEN_ROUTER_API_KEY")
OPEN_ROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
headers = {"Authorization": f"Bearer {OPEN_ROUTER_API_KEY}"}

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

def store_notification(username, title, body, user_medication_id=None):
    db = get_db()
    user = db.execute("""
                      SELECT user_id
                      FROM users
                      WHERE username = ?;
                      """, (username,)).fetchone()
    if user:
        db.execute("""
                   INSERT INTO notifications (user_id, user_medication_id, title, body)
                   VALUES (?, ?, ?, ?);
                   """, (user["user_id"], user_medication_id, title, body))
        db.commit()

# I decided to modularise the reminder_scheduler as it was getting quite large and complex.

# The overall workflow is:
#   1. Get all active medications.
#   2. Convert the current UTC time into each user's local timezone.
#   3. Check if a medication is due right now.
#   4. Send reminders (push/email) if needed.
#   5. Prevent duplicate reminders.
#   6. Detect overdue medications (if over an hour late).
#   7. Notify the user's MediMates if overdue.
#   8. Prevent duplicate overdue notifications.

# This returns all medications that are scheduled for now. They're filtered by user timezone and frequency.
def get_medications(current_time_utc):
    db = get_db()
    medications = db.execute(""" 
                             SELECT m.user_medication_id, m.user_id, u.username, u.email, m.medication_name, m.dosage_amount, m.dosage_unit, m.frequency_type, mt.time_of_day, u.timezone, m.push_notifications_enabled, m.email_notifications_enabled, mt.weekday, mt.day_of_month
                             FROM medications m JOIN medication_times mt ON m.user_medication_id = mt.user_medication_id
                             JOIN users u ON m.user_id = u.user_id
                             WHERE m.start_date <= ? AND (m.end_date IS NULL OR m.end_date >= ?);
                             """, (current_time_utc.date(), current_time_utc.date())).fetchall()
    return medications

# This checks if a reminder should be sent to the user or not based on the frequency and time.
# If frequency type is set to weekly, the weekday must match with the current day. If set to monthly,
# the day_of_month must match. If set to as needed, we never auto-remind. If set to daily, we fall
# through to time match.
def should_notify_user(medication, user_current_time):
    frequency_type = medication["frequency_type"]
    medication_time = datetime.strptime(medication["time_of_day"], "%H:%M").time()
    current_time_only = user_current_time.time().replace(second=0, microsecond=0)
    if frequency_type == "as_needed":
        return False
    if frequency_type == "weekly":
        if medication["weekday"] is None:
            return False
        if medication["weekday"] != user_current_time.weekday():
            return False
    if frequency_type == "monthly":
        if medication["day_of_month"] is None:
            return False
        current_year = user_current_time.year
        current_month = user_current_time.month
        last_day_of_current_month = pycalendar.monthrange(current_year, current_month)[1]
        scheduled_day = min(medication["day_of_month"], last_day_of_current_month)
        if scheduled_day != user_current_time.day:
            return False
    return medication_time == current_time_only

# This will send the push and email notifications to the user (if relevant)
def notify_user(medication):
    username = medication["username"]
    title = "Medication Reminder 💊"
    body = f"Hey, {username}! It's time for {medication['dosage_amount']} {medication['dosage_unit']} of {medication['medication_name']}. Keep up the great work!"
    notification_sent = False
    if medication["push_notifications_enabled"]:
        send_push_notification(
            username=username,
            title=title,
            body=body
        )
        notification_sent = True
    if medication["email_notifications_enabled"] and medication["email"]:
        send_email_notification(
            username=username,
            title=title,
            body=body
        )
        notification_sent = True
    store_notification(username, title, body, medication["user_medication_id"])
    return notification_sent

# This sends notifications to all the user's MediMates. It's used when a medication
# is overdue and a MediMate manually re-reminds them or to let them know a medication
# has been taken. 
def notify_medimates(username, title, body, user_medication_id=None):
    db = get_db()
    medimates = db.execute("""
                           SELECT u.username, u.email
                           FROM friends f JOIN users u ON u.username = f.friend2
                           WHERE f.friend1 = ?
                           """, (username,)).fetchall()
    for medimate in medimates:
        send_push_notification(medimate["username"], title, body)
        if medimate["email"]:
            send_email_notification(medimate["username"], title, body)
        store_notification(medimate["username"], title, body, user_medication_id)

# This is a helper function to determine whether a medication is overdue (by an hour) or not.
# All comparison's are done in the user's local timezone and we localise scheduled_dt to prevent
# naive datetime bugs. It returns True if overdue and False if not overdue or already logged
# as taken.
def is_medication_overdue(medication, user_current_time):
    db = get_db()
    scheduled_time = datetime.strptime(medication["time_of_day"], "%H:%M").time()
    scheduled_dt = datetime.combine(user_current_time.date(), scheduled_time)
    user_timezone = pytz.timezone(medication["timezone"]) if medication["timezone"] else pytz.utc
    if scheduled_dt.tzinfo is None:
        scheduled_dt = user_timezone.localize(scheduled_dt)
    log_exists = db.execute("""
                            SELECT 1
                            FROM medication_logs 
                            WHERE user_medication_id = ? AND scheduled_date = ? AND time_of_day = ?
                            """, (medication["user_medication_id"], user_current_time.date(), medication["time_of_day"])).fetchone()
    if not log_exists:
        return user_current_time >= scheduled_dt + timedelta(hours=1)
    else:
        return False

# This checks if a user has not marked a medication as taken within 1 hour of when it's due
# and notifies their MediMates. It also records that the overdue notification was actually
# sent to avoid sending repeated overdue alerts every minute.
def check_if_overdue_and_notify_medimates(medication, user_current_time):
    if is_medication_overdue(medication, user_current_time):
        db = get_db()
        try:
            # This inserts first to prevent duplicates
            db.execute("""
                        INSERT INTO overdue_notifications_sent (user_medication_id, scheduled_date)
                        VALUES (?, ?);
                        """, (medication["user_medication_id"], user_current_time.date()))
            db.commit()
            # This notifies MediMates only after successful insert
            title = "Medication Missed! 💊"
            body = f"{medication['username']} hasn’t marked their medication as taken yet."
            notify_medimates(medication["username"], title, body, medication["user_medication_id"])
        except IntegrityError:
            # This skips the notification if it was already sent
            pass

# This allows users to manually re-remind their MediMate to take their medication if it's overdue
# by an hour. It has some safety checks to make sure they are actually friends, confirm medication
# is overdue, and prevents duplicate reminders from the same person on the same scheduled date.
@app.route("/remind_medimate/<int:user_medication_id>", methods=["POST"])
@login_required
def remind_medimate(user_medication_id):
    db = get_db()
    # This gets the medication information and its owner
    medication = db.execute("""
                            SELECT m.user_medication_id, m.user_id, m.medication_name, m.dosage_amount, m.dosage_unit, u.username, u.timezone, mt.time_of_day
                            FROM medications m JOIN users u ON m.user_id = u.user_id
                            JOIN medication_times mt ON m.user_medication_id = mt.user_medication_id
                            WHERE m.user_medication_id = ?
                            """, (user_medication_id,)).fetchone()
    if medication:
        medimate_username = medication["username"]
        # This ensures that they are actually MediMates
        is_medimate = db.execute("""
                                 SELECT 1
                                 FROM friends
                                 WHERE (friend1 = ? AND friend2 = ?) OR (friend1 = ? AND friend2 = ?)
                                 """, (session["username"], medimate_username, medimate_username, session["username"])).fetchone()
        if is_medimate:
            current_time_utc = datetime.now(timezone.utc)
            user_timezone = pytz.timezone(medication["timezone"]) if medication["timezone"] else pytz.utc
            user_current_time = current_time_utc.astimezone(user_timezone)
            if is_medication_overdue(medication, user_current_time):
                try:
                    db.execute("""
                               INSERT INTO medimate_reminders_sent (user_medication_id, reminded_by, scheduled_date)
                               VALUES (?, ?, ?);
                               """, (user_medication_id, session["username"], user_current_time.date()))
                    db.commit()
                    # This notifies the user only after successful insert
                    title = "Your MediMate is reminding you! 💊"
                    body = f"{session['username']} is reminding you that it's time for {medication['dosage_amount']} {medication['dosage_unit']} of {medication['medication_name']}!"
                    send_push_notification(medimate_username, title, body)
                    send_email_notification(medimate_username, title, body)
                    store_notification(medimate_username, title, body, user_medication_id)
                except IntegrityError:
                    pass
    return redirect( url_for("notification_centre") )

# This is the main background job. It runs once every minute via the background scheduler.
# For every active medication, it converts the current UTC time to the user's timezone (to ensure
# they get the reminder at their local time), checks if a reminder should be sent now, prevents
# duplicate notifications being sent using the medication_reminders_sent table, sends reminders
# if required, checks if a medication is overdue and notifies the user's MediMates if so.
def reminder_scheduler():
    with app.app_context():
        current_time_utc = datetime.now(timezone.utc)
        medications = get_medications(current_time_utc)
        db = get_db()
        for medication in medications:
            # This converts the current UTC time into the user's local timezone
            user_time_zone = pytz.timezone(medication["timezone"]) if medication["timezone"] else pytz.utc
            user_current_time = current_time_utc.astimezone(user_time_zone)
            # This is for user reminders
            if should_notify_user(medication, user_current_time):
                # This avoids sending duplicate notifications
                try:
                    db.execute("""
                               INSERT INTO medication_reminders_sent (user_medication_id, time_of_day, date_sent)
                               VALUES (?, ?, ?);
                               """, (medication["user_medication_id"], medication["time_of_day"], user_current_time.date()))
                    db.commit()
                    # This notifies the user only after successful insert
                    notify_user(medication)
                except IntegrityError:
                    # This skips the notification if it was already sent
                    pass
            # This is for overdue notifications to MediMates
            check_if_overdue_and_notify_medimates(medication, user_current_time)

# This background scheduler runs reminder_scheduler() automatically in the background once every minute
# (this doesn't stop the app from serving requests). By running it every minute we ensure we don't miss a 
# scheduled time (since medications are matched at minute precision / HH:MM). replace_existing = True 
# ensures only one reminder_scheduler job is active even if the app reloads. The scheduler starts when the 
# app starts and continues running as long as the the server process is alive.
scheduler = BackgroundScheduler()
scheduler.add_job(reminder_scheduler, "interval", minutes=1, replace_existing=True)
scheduler.start()

@app.route("/month_calendar/<int:year>/<int:month>")
@login_required
def month_calendar(year, month):
    calendar_year = build_month_calendar(g.user["user_id"], year, month)
    today = date.today()
    month_name = pycalendar.month_name[month]
    if month == 1:
        prev_month = 12
        prev_year = year -1
    else:
        prev_month = month - 1
        prev_year = year
    if month == 12:
        next_month = 1
        next_year = year + 1
    else: 
        next_month = month + 1
        next_year = year
    return render_template("month_calendar.html", calendar=calendar_year, year=year, month=month, month_name=month_name, today=today, prev_month=prev_month, prev_year=prev_year, next_month=next_month, next_year=next_year)

#monthly calendar view - to be improved
@app.route("/month_calendar")
@login_required
def calendar():
    today = date.today()
    return redirect(url_for("month_calendar", year=today.year, month=today.month))

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

'''This builds a simplified weekly status summary for the dashboard.
It shows whether the user has any meds scheduled/ marked as taken or not'''
def build_week_status(user_id):
    detailed_calendar = build_week_calendar(user_id)
    status_calendar = {}
    for day, meds in detailed_calendar.items():
        if not meds: #if no medications scheduled that day:
            status_calendar[day] = {
                "all_taken": False, #no meds taken
                "has_meds": False #no meds scheduled
            }
        else:
            all_taken = all(med["taken"] for med in meds) #checks if all meds for that day are marked taken
            status_calendar[day] = {
                "all_taken": all_taken,
                "has_meds": True
            }
    return status_calendar

'''this is a build of a proper month-style grid. Needs more work done for this part - maybe put as an option to view whole month in log medication'''
def build_month_calendar(user_id, year, month):
    db = get_db()
    first_weekday, days_in_month = pycalendar.monthrange(year, month)
    first_day = date(year, month, 1)
    start_grid = first_day - timedelta(days=first_day.weekday())
    medications = db.execute("""
        SELECT m.user_medication_id, m.medication_name,
               m.frequency_type, m.start_date, m.end_date,
               mt.time_of_day, mt.weekday
        FROM medications m
        JOIN medication_times mt
        ON m.user_medication_id = mt.user_medication_id
        WHERE m.user_id = ?
    """, (user_id,)).fetchall()
    today = date.today()
    calendar = []

    for i in range(42):  # 6 week grid
        current_day = start_grid + timedelta(days=i)

        scheduled = 0
        taken = 0

        for medication in medications:

            if current_day < medication["start_date"]:
                continue
            if medication["end_date"] and current_day > medication["end_date"]:
                continue

            include = False

            if medication["frequency_type"] == "daily":
                include = True

            elif medication["frequency_type"] == "weekly":
                include = medication["weekday"] == current_day.weekday()

            elif medication["frequency_type"] == "monthly":
                if medication["day_of_month"] is not None:
                    last_day = pycalendar.monthrange(
                        current_day.year,
                        current_day.month
                    )[1]
                    scheduled_day = min(
                        medication["day_of_month"],
                        last_day
                    )
                    include = scheduled_day == current_day.day

            if include:
                scheduled += 1

                log = db.execute("""
                    SELECT 1 FROM medication_logs
                    WHERE user_medication_id = ?
                    AND scheduled_date = ?
                    AND time_of_day = ?
                """, (
                    medication["user_medication_id"],
                    current_day,
                    medication["time_of_day"]
                )).fetchone()

                if log:
                    taken += 1

        # Determine day status
        if scheduled == 0:
            status = "none"
        elif taken == scheduled:
            status = "complete"
        elif taken > 0:
            status = "partial"
        else:
            status = "missed"

        calendar.append({
            "date": current_day,
            "in_month": current_day.month == month,
            "scheduled": scheduled,
            "taken": taken,
            "status": status,
            "is_today": current_day == today
        })

    return calendar

def calculate_streak(user_id):
    db = get_db()
    today = date.today()
    streak_total = 0
    current_day = today
    # This will get earliest medication start date
    earliest_med = db.execute("""
        SELECT MIN(start_date) as earliest
        FROM medications
        WHERE user_id = ?
    """, (user_id,)).fetchone()
    if not earliest_med or not earliest_med["earliest"]:
        return 0
    earliest_start = datetime.strptime(
        earliest_med["earliest"], "%Y-%m-%d"
    ).date()
    while current_day >= earliest_start:
        meds = db.execute("""
            SELECT m.user_medication_id, mt.time_of_day, 
                   m.frequency_type, mt.weekday, mt.day_of_month
            FROM medications m
            JOIN medication_times mt 
            ON m.user_medication_id = mt.user_medication_id
            WHERE m.user_id = ?
            AND m.start_date <= ?
            AND (m.end_date IS NULL OR m.end_date >= ?)
        """, (user_id, current_day, current_day)).fetchall()
        # This part filters by frequency
        filtered_meds = []
        for med in meds:
            include = False
            if med["frequency_type"] == "daily":
                include = True
            elif med["frequency_type"] == "weekly":
                if med["weekday"] == current_day.weekday():
                    include = True
            elif med["frequency_type"] == "monthly":
                if med["day_of_month"] == current_day.day:
                    include = True
            if include:
                filtered_meds.append(med)
        # If no meds scheduled that day, then skip
        if not filtered_meds:
            current_day -= timedelta(days=1)
            continue
        # This checks if all meds are taken
        all_taken = True
        for med in filtered_meds:
            log = db.execute("""
                SELECT 1 FROM medication_logs
                WHERE user_medication_id = ?
                AND scheduled_date = ?
                AND time_of_day = ?
            """, (med["user_medication_id"], current_day, med["time_of_day"])).fetchone()
            if not log:
                all_taken = False
                break
        if all_taken:
            streak_total += 1
            current_day -= timedelta(days=1)
        else:
            break
    return streak_total

def get_adherence_data(user_id, start_date=None, end_date=None):
    db = get_db()
    if not start_date or not end_date:
        today = date.today()
        start_date = today - timedelta(days=29)
        end_date = today
    results = []
    current_day = start_date
    today = date.today()
    while current_day <= end_date:
        if current_day > today:
            results.append({
                "date": current_day.strftime("%Y-%m-%d"),
                "adherence": None
            })
            current_day += timedelta(days=1)
            continue
        meds = db.execute("""
            SELECT m.user_medication_id, mt.time_of_day,
                   m.frequency_type, mt.weekday, mt.day_of_month
            FROM medications m
            JOIN medication_times mt
            ON m.user_medication_id = mt.user_medication_id
            WHERE m.user_id = ?
            AND m.start_date <= ?
            AND (m.end_date IS NULL OR m.end_date >= ?)
        """, (
            user_id,
            current_day.strftime("%Y-%m-%d"),
            current_day.strftime("%Y-%m-%d")
        )).fetchall()
        scheduled = 0
        taken = 0
        for med in meds:
            include = False
            if med["frequency_type"] == "daily":
                include = True
            elif med["frequency_type"] == "weekly":
                if med["weekday"] == current_day.weekday():
                    include = True
            elif med["frequency_type"] == "monthly":
                if med["day_of_month"] == current_day.day:
                    include = True
            if include:
                scheduled += 1
                log = db.execute("""
                    SELECT 1 FROM medication_logs
                    WHERE user_medication_id = ?
                    AND scheduled_date = ?
                    AND time_of_day = ?
                """, (
                    med["user_medication_id"],
                    current_day.strftime("%Y-%m-%d"),
                    med["time_of_day"]
                )).fetchone()
                if log:
                    taken += 1
        if scheduled > 0:
            adherence = round((taken / scheduled) * 100)
        else:
            adherence = 0
        results.append({
            "date": current_day.strftime("%Y-%m-%d"),
            "adherence": adherence
        })
        current_day += timedelta(days=1)
    return results

# This is the home page route.
@app.route("/")
@login_required
def index():
    calendar_status = None
    current_streak = 0
    chart_data = []
    month_name = None
    db = get_db()
    user_id = g.user["user_id"]
    calendar_status = build_week_status(user_id)
    current_streak = calculate_streak(user_id)
    today = date.today()
    start_date = date(today.year, today.month, 1)
    last_day = pycalendar.monthrange(today.year, today.month)[1]
    end_date = date(today.year, today.month, last_day)
    month_name = pycalendar.month_name[today.month]
    chart_data = get_adherence_data(
        user_id,
        start_date,
        end_date
    )
    total_scheduled = 0
    total_taken = 0
    for day in chart_data:
        if day["adherence"] is not None:
            # We need scheduled + taken from database instead of %
            day_date = day["date"]
            scheduled_count = db.execute("""
                SELECT COUNT(*) 
                FROM medications m
                JOIN medication_times mt 
                ON m.user_medication_id = mt.user_medication_id
                WHERE m.user_id = ?
                AND m.start_date <= ?
                AND (m.end_date IS NULL OR m.end_date >= ?)
            """, (user_id, day_date, day_date)).fetchone()[0]
            taken_count = db.execute("""
                SELECT COUNT(*)
                FROM medication_logs ml
                JOIN medications m
                ON ml.user_medication_id = m.user_medication_id
                WHERE m.user_id = ?
                AND ml.scheduled_date = ?
            """, (user_id, day_date)).fetchone()[0]
            total_scheduled += scheduled_count
            total_taken += taken_count
    if total_scheduled > 0:
        average_adherence = round((total_taken / total_scheduled) * 100)
    else:
        average_adherence = 0
    active_medications = db.execute("""SELECT COUNT(*) FROM medications WHERE user_id = ? AND  (end_date IS NULL OR end_date >= ?)""", (user_id, today)).fetchone()[0]
    return render_template(
        "index.html", title="Home", calendar=calendar_status, streak=current_streak, chart_data=chart_data, month_name=month_name, average_adherence=average_adherence, active_medications=active_medications
    )

# This provides the number of unread notifications to be shown in the nav bar next to
# notification centre
@app.context_processor
def provide_unread_notification_count():
    unread_notification_count = 0
    if "username" not in session:
        return dict(unread_notification_count=unread_notification_count)
    db = get_db()
    user = db.execute("""
                      SELECT user_id
                      FROM users
                      WHERE username = ?;
                      """, (session["username"],)).fetchone()
    if user:
        unread_notification_count = db.execute("""
                                               SELECT COUNT(*) as count
                                               FROM notifications
                                               WHERE user_id = ? AND is_read = 0;
                                               """, (user["user_id"],)).fetchone()["count"]
    return dict(unread_notification_count=unread_notification_count)

# Provides the number of unread notifications to show in the nav bar
@app.context_processor
def provide_unread_notification_count():
    if "username" not in session:
        return dict(unread_notification_count=0)

    db = get_db()
    user = db.execute("""
        SELECT user_id
        FROM users
        WHERE username = ?;
    """, (session["username"],)).fetchone()

    if not user:
        return dict(unread_notification_count=0)

    count = db.execute("""
        SELECT COUNT(*) as count
        FROM notifications
        WHERE user_id = ? AND is_read = 0;
    """, (user["user_id"],)).fetchone()["count"]

    return dict(unread_notification_count=count)

@app.route("/notification_centre")
@login_required
def notification_centre():
    db = get_db()
    username = session["username"]
    user = db.execute("""
                      SELECT *
                      FROM users
                      WHERE username = ?;
                      """, (username,)).fetchone()
    notifications = []
    if user:
        user_id = user["user_id"]
        notifications = db.execute("""
                                   SELECT *
                                   FROM notifications
                                   WHERE user_id = ?
                                   ORDER BY created_at DESC;
                                   """, (user_id,)).fetchall()
        notifications = [dict(n) for n in notifications]
        current_time_utc = datetime.now(timezone.utc)
        for notification in notifications:
            notification["overdue"] = False
            if notification["user_medication_id"]:
                medication = db.execute("""
                                        SELECT m.*, mt.time_of_day, u.timezone
                                        FROM medications m JOIN medication_times mt ON m.user_medication_id = mt.user_medication_id
                                        JOIN users u ON m.user_id = u.user_id
                                        WHERE m.user_medication_id = ?;
                                        """, (notification["user_medication_id"],)).fetchone()
                if medication:
                    user_timezone = pytz.timezone(medication["timezone"]) if medication["timezone"] else pytz.utc
                    user_current_time = current_time_utc.astimezone(user_timezone)
                    notification["overdue"] = is_medication_overdue(medication, user_current_time)
    return render_template("notification_centre.html", title="Notification Centre", notifications=notifications)

@app.route("/notification_centre/mark_read/<int:notification_id>", methods=["POST"])
@login_required
def mark_notification_as_read(notification_id):
    db = get_db()
    username = session["username"]
    user = db.execute("""
                      SELECT *
                      FROM users
                      WHERE username = ?;
                      """, (username,)).fetchone()
    if user:
        user_id = user["user_id"]
        db.execute("""
                UPDATE notifications
                SET is_read = 1
                WHERE notification_id = ? AND user_id = ?
                """, (notification_id, user_id))
        db.commit()
    return redirect( url_for("notification_centre") )

# This displays the weekly calendar in log medication
@app.route("/log_medication_week")
@login_required
def log_medication_week():
    calendar = build_week_calendar(g.user["user_id"])
    return render_template("log_medication.html", calendar=calendar)

#This shows the detailed weekly calendar with medications and allows users to log meds as taken or not
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
        # This notifies the user's MediMates that they have taken their medication
        user = db.execute("""
                          SELECT u.user_id, u.username
                          FROM users u JOIN medications m ON m.user_id = u.user_id
                          WHERE m.user_medication_id = ?
                          """, (user_medication_id,)).fetchone()
        if user:
            # This marks the weekly summary as outdated
            db.execute("""
                    UPDATE users
                    SET weekly_summary_outdated = 1
                    WHERE user_id = ?;
                    """, (user["user_id"],))
            title = "Medication Taken! 💊"
            body = f"{user['username']} has just taken their medication!"
            notify_medimates(user["username"], title, body, user_medication_id)
        db.commit()
    return redirect( url_for("log_medication_week") )

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
    send_push_notification(session["username"], "Test", "This is a test")
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

@app.route("/delete_medication/<int:user_medication_id>", methods=["POST"])
@login_required
def delete_medication(user_medication_id):
    db = get_db()
    db.execute("""
               DELETE FROM medication_times WHERE user_medication_id = ?""", (user_medication_id,))
    db.execute("""DELETE FROM medication_logs WHERE user_medication_id = ?""", (user_medication_id,))
    db.execute("""DELETE FROM medications WHERE user_medication_id = ? AND user_id = ?""",(user_medication_id, g.user["user_id"]))
    db.commit()
    return redirect(url_for("history"))

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
    store_notification(friend1, title, body)

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
    store_notification(sender, title, body)
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
            return render_template("medimates.html", title="Add Mates", form=form, response=response)
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
        
        existing_friend = db.execute("""
                                     SELECT *
                                     FROM friends
                                     WHERE friend1 = ? AND friend2 = ?;
                                     """, (user, receiver,)).fetchone()
        
        mutual_invite = db.execute("""
                                     SELECT *
                                     FROM invites
                                     WHERE sender = ? AND receiver = ?;
                                     """, (receiver, user,)).fetchone()
        
        if existing_friend is not None:
            form.username.errors.append("You are already friends with this user.")
        elif existing_invite is not None:
            form.username.errors.append("You have already sent this user an invite.")
        elif mutual_invite is not None:
            db.execute("""
                INSERT INTO friends (friend1, friend2)
                VALUES
                (?, ?);
                """, (user, receiver,))
    
            db.execute("""
                INSERT INTO friends (friend1, friend2)
                VALUES
                (?, ?);
                """, (receiver, user,))
            
            db.execute("""
               DELETE FROM invites
               WHERE sender = ? AND receiver = ?;
               """, (receiver, user,))
            db.commit()
            response = "This user has also sent you an invite. You are now MediMates!"
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
            store_notification(receiver, title, body)
        else:
            form.username.errors.append("This user does not exist.")

    medimates = db.execute("""
                    SELECT f.friend2, u.user_id, u.allow_mates_activity, u.profile_picture
                    FROM friends AS f
                    JOIN users AS u ON f.friend2 = u.username
                    WHERE f.friend1 = ?""", (user,))
    
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

@app.route("/medimate_medimate/<int:friend_id>")
@login_required
def medimate_meds(friend_id):
    db = get_db()
    meds = db.execute("""
                    SELECT u.username, m.medication_name, m.dosage_amount, m.dosage_unit, m.start_date, m.end_date
                    FROM users AS u
                    JOIN medications AS m ON m.user_id = u.user_id
                    WHERE  u.user_id = ? AND u.allow_mates_activity == 1""", (friend_id,)).fetchall()
    return render_template("medimate_meds.html", title="Medimates Meds", meds=meds)


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
        db.execute("""
                   UPDATE users
                   SET weekly_summary_outdated = 1
                   WHERE user_id = ?
                   """, (user["user_id"],))
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

@app.route("/history/report")
@login_required
def history_report():
    db = get_db()
    user = db.execute("""
                      SELECT * 
                      FROM users 
                      WHERE username = ?
                      """, (session["username"],)).fetchone()
    medications = db.execute("""
                          SELECT *
                          FROM medications
                          WHERE user_id = ?
                          ORDER BY start_date DESC
                          """, (user["user_id"],)).fetchall()
    total_meds = len(medications)
    return render_template("medication_report.html", user=user, medications=medications, total_meds=total_meds, generated_on=datetime.now())

# This is for generating AI weekly summaries
# The way it works is by getting all the user's medication logs and symptom logs from the past week, formatting
# them into a summary prompt to give to the AI, asking the AI to write a weekly health summary and then returning
# it for display.
def generate_weekly_health_summary(user_id):
    db = get_db()
    # This gets the last 7 days
    today = date.today()
    # This checks if the summary is up to date
    user = db.execute("""
                      SELECT weekly_summary, weekly_summary_outdated
                      FROM users
                      WHERE user_id = ?;
                      """, (user_id,)).fetchone()
    if user and user["weekly_summary"] and not user["weekly_summary_outdated"]:
        return user["weekly_summary"]
    # If it's outdated, generate new summary
    week_start = today - timedelta(days=6)
    # This gets the medication logs
    medications = db.execute("""
                             SELECT m.medication_name, ml.scheduled_date, ml.time_of_day
                             FROM medication_logs ml
                             JOIN medications m ON ml.user_medication_id = m.user_medication_id
                             WHERE m.user_id = ? AND ml.scheduled_date BETWEEN ? AND ?
                             ORDER BY ml.scheduled_date ASC
                             """, (user_id, week_start, today)).fetchall()
    # This gets the symptom logs
    symptoms = db.execute("""
                          SELECT symptom_name, severity, symptom_date
                          FROM symptoms
                          WHERE user_id = ? AND symptom_date BETWEEN ? AND ?
                          ORDER BY symptom_date ASC
                          """, (user_id, week_start, today)).fetchall()
    # This will start to build the information needed to give the AI
    summary_data = "Weekly Health Data:\n\nMedication Taken:\n"
    if medications:
        for medication in medications:
            summary_data += f"{medication['medication_name']} on {medication['scheduled_date']} at {medication['time_of_day']}\n"
    else:
        summary_data += "No medication logged.\n"
    summary_data += "\nSymptoms Experienced:\n"
    if symptoms:
        for symptom in symptoms:
            summary_data += f"{symptom['symptom_name']} (Severity: {symptom['severity']}) on {symptom['symptom_date']}\n"
    else:
        summary_data += "No symptoms logged.\n"
    # This builds the prompt to give the AI
    prompt = f"""
              You are a friendly health assistant. Summarise the following user's weekly health data in a concise, positive, and
              understandable paragraph, giving gently reminders or encouragements if needed:
              {summary_data}
              """
    # This calls the OpenRouter API
    try:
        response = requests.post(
            OPEN_ROUTER_API_URL,
            headers=headers,
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=15
        )
        data = response.json()
        if "choices" in data and len(data["choices"]) > 0:
            summary = data["choices"][0]["message"]["content"]
        else:
            summary = f"AI summary is temporarily unavailable. API returned unexpected response: {data}\n\n{summary_data}"
    except Exception as e:
        summary = f"AI summary is temporarily unavailable. Reason: {str(e)}\n\n{summary_data}"
    # This saves the new summary and sets the weekly summary as up to date.
    db.execute("""
               UPDATE users
               SET weekly_summary = ?, weekly_summary_outdated = 0
               WHERE user_id = ?
               """, (summary, user_id))
    db.commit()
    return summary

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
        WHERE friend1 = ?
        """,
        (session["username"],),
    ).fetchone()[0]
    # This generates the AI weekly summary
    weekly_summary = generate_weekly_health_summary(user["user_id"])
    return render_template("profile.html", user=user, mates=mates,mode="view", weekly_summary=weekly_summary)

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
    return render_template("profile.html", user=user, avatars=avatars, mode="edit")

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

    if preferences_form.submit.data and preferences_form.validate_on_submit():
        db.execute(
            """UPDATE users SET allow_mates_activity = ? WHERE user_id = ?""",
            (preferences_form.allow_mates_activity.data, user["user_id"]),
        )
        db.commit()
        flash("Privacy preference updated successfully")
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