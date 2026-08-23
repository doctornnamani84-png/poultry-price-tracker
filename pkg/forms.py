from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FloatField, SelectField, DateField, SubmitField
from wtforms.validators import DataRequired, Email, Length

class LoginForm(FlaskForm):  # <-- this is what VS Code is shouting for
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login') 

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Register') 

class DayOldPriceForm(FlaskForm):
    hatchery_id = SelectField('Hatchery', coerce=int, validators=[DataRequired()])
    bird_type = StringField('Bird Type', validators=[DataRequired()])
    price = FloatField('Price ₦', validators=[DataRequired()])
    availability = SelectField('Availability', choices=[('Available', 'Available'), ('Out of Stock', 'Out of Stock'), ('Pre-order', 'Pre-order')], validators=[DataRequired()])
    state_id = SelectField('State', coerce=int, validators=[DataRequired()])
    lga_id = SelectField('LGA', coerce=int)
    price_date = DateField('Price Date', format='%Y-%m-%d', validators=[DataRequired()])
    day_of_week = SelectField('Day of Week', 
        choices=[('Monday','Monday'),('Tuesday','Tuesday'),('Wednesday','Wednesday'),('Thursday','Thursday'),('Friday','Friday'),('Saturday','Saturday'),('Sunday','Sunday')],
        validators=[DataRequired()])
    submit = SubmitField('Submit for Approval')     