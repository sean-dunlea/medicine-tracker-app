from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, DateField, TextAreaField
from wtforms.validators import DataRequired, Length, EqualTo, Regexp, InputRequired

username_rule = Regexp(
    r"^[A-Za-z0-9_.-]+$",
    message="Username can contain letters, numbers, dots, hyphens, and underscores only."
)

class LoginForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[
            DataRequired(message="Username is required."),
            Length(min=3, max=30, message="Usernamen must be 3-30 characters"),
        ],
        render_kw={
            "autocomplete": "username",
            "autofocus": True,
            "placeholder": "Enter your username",
        },
    )

    password = PasswordField(
        "Password",
        validators=[DataRequired(message="Password is required.")],
        render_kw={
            "autocomplete": "current-password",
            "placeholder": "Enter your password",
        },
    )

    remember = BooleanField("Remember me")
    submit = SubmitField("Sign in")


class RegistrationForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[
            DataRequired(message="Username is required."),
            Length(min=3, max=30, message="Username must be 3–30 characters."),
            username_rule,
        ],
        render_kw={
            "autocomplete": "username",
            "placeholder": "Choose a username",
        },
    )

    password = PasswordField(
        "Password",
        validators=[
            DataRequired(message="Password is required."),
            Length(min=8, message="Password must be at least 8 characters."),
        ],
        render_kw={
            "autocomplete": "new-password",
            "placeholder": "Create a password (min 8 chars)",
        },
    )

    confirm_password = PasswordField(
        "Confirm password",
        validators=[
            DataRequired(message="Please confirm your password."),
            EqualTo("password", message="Passwords must match."),
        ],
        render_kw={
            "autocomplete": "new-password",
            "placeholder": "Repeat your password",

        },
    )

    submit = SubmitField("Create account")

class AddMedicationForm(FlaskForm):
    medication_name = StringField("Medication Name", validators=[InputRequired()], render_kw={"placeholder": "e.g. Paracetamol"})
    dosage = StringField("Dosage", validators=[InputRequired()], render_kw={"placeholder": "e.g. 200 mg"})
    frequency = SelectField("Frequency", choices=[("once_per_day", "Once per day"), ("twice_per_day", "Twice per day"), ("three_times_per_day", 
    "Three times per day"), ("as_needed", "As needed")])
    time_of_day = StringField("Time of Day", render_kw={"placeholder": "e.g. 08:00, 20:00"})
    start_date = DateField("Start Date", validators=[InputRequired()], format="%Y-%m-%d")
    end_date = DateField("End Date", format="%Y-%m-%d")
    instructions = TextAreaField("Instructions", render_kw={"placeholder": "e.g. Take with food"})
    reminders_enabled = BooleanField("Enable reminders")
    submit = SubmitField("Add medication")
