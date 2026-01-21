from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
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