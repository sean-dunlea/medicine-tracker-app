#!/usr/bin/env python3
from flask import Flask, render_template, redirect, url_for, session, g, request
# Server-side session management
from flask_session import Session
from forms import RegistrationForm, LoginForm
from database import get_db, close_db
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
# Secret key for signing sessions to protect against CSRF attacks.
app.config["SECRET_KEY"] = "this-is-my-secret-key"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"

Session(app)

# Ensures the database connection is closed after each request.
app.teardown_appcontext(close_db)

# This will run before every request. It avoids repeating session.get()
# everywhere and makes the decorators cleaner.
@app.before_request
def load_logged_in_user():
    g.user = session.get("username", None)

# This is unused at the moment but we might need it later to protect routes
# that require a user to be logged in.
def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("login", next=request.url))
        return view(*args, **kwargs)
    return wrapped_view

# This is the home page route.
@app.route("/")
def index():
    return render_template("index.html", title="Home")

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
            next_page = request.args.get("next")
            if not next_page:
                next_page = url_for("index")
            return redirect(next_page)
    return render_template("login.html", title="Login", form=form)

if __name__ == "__main__":
    app.run(debug=True)