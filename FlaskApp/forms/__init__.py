from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, DateField, MultipleFileField, SelectField, SubmitField, PasswordField
from wtforms.validators import DataRequired, EqualTo
import datetime


class RegisterForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    email = EmailField("Email", validators=[DataRequired()])
    password_hash = PasswordField('Password', validators=[DataRequired(), EqualTo(
        'password_hash2', message='Passwords Must Match!')])
    password_hash2 = PasswordField(
        'Confirm Password', validators=[DataRequired()])
    submit = SubmitField("Submit")


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Submit")


class SelectForm(FlaskForm):
    file_type = SelectField('File Type', coerce=str,
                            validators=[DataRequired()])
    file_name = SelectField('File Name', coerce=str,
                            validators=[DataRequired()])
    submit = SubmitField('Download')


class UploadForm(FlaskForm):
    file = MultipleFileField('File(s) Upload', validators=[DataRequired()])
    submit = SubmitField('Upload')


class DataForm(FlaskForm):
    file_name = SelectField('File Name', coerce=str)
    start_date = DateField(
        'Start date', format="%Y-%m-%d", default=datetime.datetime.strptime('1970-01-01', '%Y-%m-%d'))
    end_date = DateField(
        'End date', format="%Y-%m-%d", default=datetime.datetime.today())
    submit = SubmitField('Get')



class UpdateForm(FlaskForm):
    username = StringField("Username", validators=[
                           DataRequired()])
    password_hash = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField("Update")
