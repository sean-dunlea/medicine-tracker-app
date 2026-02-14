from flask_wtf import FlaskForm
from wtforms import EmailField, StringField, PasswordField, BooleanField, SubmitField, DecimalField, SelectField, IntegerField, TimeField, FieldList, DateField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Regexp, InputRequired, NumberRange, Optional

username_rule = Regexp(r"^[A-Za-z0-9_.-]+$", message="Username can contain letters, numbers, dots, hyphens, and underscores only.")

class LoginForm(FlaskForm):
    # Changed variable name to "identifier" as users may enter either their username or email.
    identifier = StringField("Username or Email", validators=[DataRequired(message="Username is required."), Length(min=3, max=30, message="Username must be 3-30 characters"),],
        render_kw={"autocomplete": "username", "autofocus": True, "placeholder": "Enter your username",},)
    password = PasswordField("Password", validators=[DataRequired(message="Password is required.")], render_kw={"autocomplete": "current-password", "placeholder": 
        "Enter your password",},)
    remember = BooleanField("Remember me")
    submit = SubmitField("Sign in")

class RegistrationForm(FlaskForm):
    email = EmailField("Email: ", validators=[DataRequired(message="Email is required."), Email(message="Please enter a valid email address.")], 
        render_kw={"autocomplete": "email", "placeholder": "Enter your email address"})
    username = StringField("Username", validators=[DataRequired(message="Username is required."), Length(min=3, max=30, message="Username must be 3–30 characters."), 
        username_rule,], render_kw={"autocomplete": "username", "placeholder": "Choose a username",},)
    password = PasswordField("Password", validators=[DataRequired(message="Password is required."), Length(min=8, message="Password must be at least 8 characters."),],
        render_kw={"autocomplete": "new-password", "placeholder": "Create a password (min 8 chars)",},)
    confirm_password = PasswordField("Confirm password", validators=[DataRequired(message="Please confirm your password."), EqualTo("password", message="Passwords must match."),],
        render_kw={"autocomplete": "new-password", "placeholder": "Repeat your password",},)
    submit = SubmitField("Create account")

class AddMedicationForm(FlaskForm):
    medication_name = StringField("Medication Name", validators=[InputRequired()], render_kw={"placeholder": "Paracetamol"})
    dosage_amount = DecimalField("Dosage", places=2, validators=[InputRequired(), NumberRange(min=0.01)], render_kw={"step": "1", "placeholder": "10"})
    dosage_unit = SelectField("", choices=[("mg", "mg"), ("ml", "ml"), ("tablet", "tablet(s)"), ("application", "application(s)")])
    frequency_count = IntegerField("Frequency", validators=[InputRequired(), NumberRange(min=1, max=10)], render_kw={"step": "1", "placeholder": "1"})
    frequency_type = SelectField("", choices=[("daily", "Daily"), ("weekly", "Weekly"), ("monthly", "Monthly"), ("as_needed", "As needed")])
    time_of_day = FieldList(TimeField("Time of Day"), min_entries=1)
    start_date = DateField("Start Date", validators=[InputRequired()], format="%Y-%m-%d")
    end_date = DateField("End Date", format="%Y-%m-%d")
    instructions = TextAreaField("Further Instructions (Optional)", render_kw={"placeholder": "e.g. Take with food"})
    push_notifications_enabled = BooleanField("Enable push notifications")
    submit = SubmitField("Add medication")

class AddMateForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(message="Username is required."), Length(min=3, max=30, message="Username must be 3-30 characters"),],
    render_kw={"placeholder": "Enter your username",},)
    submit = SubmitField("Send invite")

class LogSymptomForm(FlaskForm):
    symptom_name = StringField("Symptom", validators=[DataRequired(message="Please enter a symptom.")])
    severity = SelectField("Severity", choices=[("1", "1 - Very Mild"), ("2", "2 - Mild"), ("3", "3 - Moderate"),("4", "4 - Severe"), ("5", "5 - Very Severe"),], 
        validators=[DataRequired()])
    symptom_date = DateField("Date", validators=[DataRequired()], format="%Y-%m-%d")
    symptom_time = TimeField("Time", validators=[Optional()], format="%H:%M")
    notes = TextAreaField("Notes", validators=[Optional()])
    submit = SubmitField("Log Symptom")