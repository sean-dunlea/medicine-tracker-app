from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, DateField, TextAreaField, BooleanField, SubmitField
from wtforms.validators import InputRequired, EqualTo

class RegistrationForm(FlaskForm):
    username = StringField("", validators=[InputRequired()], render_kw={"placeholder": "Username"})
    password = PasswordField("", validators=[InputRequired()], render_kw={"placeholder": "Password"})
    confirm_password = PasswordField("", validators=[InputRequired(), EqualTo("password")], render_kw={"placeholder": "Confirm Password"})
    submit = SubmitField("Register")

class LoginForm(FlaskForm):
    username = StringField("", validators=[InputRequired()], render_kw={"placeholder": "Username"})
    password = PasswordField("", validators=[InputRequired()], render_kw={"placeholder": "Password"})
    submit = SubmitField("Login")

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