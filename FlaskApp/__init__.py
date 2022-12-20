from flask import Flask, flash, session, redirect, url_for, render_template, request
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from .forms import RegisterForm, LoginForm, SelectForm, UploadForm, DataForm, UpdateForm
from dotenv import load_dotenv
import datetime
from .models import db, User, Nasdaq
import jwt
from flask_migrate import Migrate
import os
import uuid
from .extract import Extract
from .sendEmail import Email
from werkzeug.utils import secure_filename
import pandas as pd


app = Flask(__name__)
app.config['SECRET_KEY'] = "This is my secret key!"

load_dotenv()
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_HOST = os.environ.get('DB_HOST')
DB_PORT = os.environ.get('DB_PORT')
ODBC = os.environ.get('ODBC')
connection_string = os.environ.get('connection_string')
website = os.environ.get('website')

ALLOWED_EXTENSIONS = set(['csv', 'json'])
UPLOAD_FOLDER = '.\\FlaskApp\\uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = 'thisissecret'
app.config['SQLALCHEMY_DATABASE_URI'] = f"mssql+pyodbc://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?driver=ODBC+Driver+17+for+SQL+Server"
db.init_app(app)
migrate = Migrate(app, db)
extract = Extract()
sendEmail = Email(connection_string)
def allowed_file(fileName):
    return '.' in fileName and fileName.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


def token_encode(public_id):
    token = jwt.encode({'public_id': public_id, 'exp': datetime.datetime.utcnow(
    ) + datetime.timedelta(minutes=300)}, app.config['SECRET_KEY'], 'HS256')
    session['token'] = token
    return token


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'token' in session:
            token = session.get('token')
        elif 'token=' in str(request.url):
            token_string = str(request.url)
            loc = token_string.split('token=')
            token = loc[1]
        if not token:
            return redirect(url_for('login'))
        try:
            data = jwt.decode(
                token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.filter_by(
                public_id=data['public_id']).first()
        except:
            return render_template('500.html'), 500
        return f(current_user, *args, **kwargs)
    return decorated


def admin_control(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'token' in session:
            token = session.get('token')
        elif 'token=' in str(request.url):
            token_string = str(request.url)
            loc = token_string.split('token=')
            token = loc[1]
        if not token:
            return redirect(url_for('login'))
        try:
            data = jwt.decode(
                token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.filter_by(
                public_id=data['public_id']).first()
            if not current_user.admin:
                return render_template('500.html'), 500
        except:
            return render_template('500.html'), 500
        return f(current_user, *args, **kwargs)
    return decorated


@app.route('/register', methods=['POST', 'GET'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        email = User.query.filter_by(email=form.email.data).first()
        username = User.query.filter_by(name=form.username.data).first()
        if email is None and username is None:
            public_id = str(uuid.uuid4())
            hashed_password = generate_password_hash(
                form.password_hash.data, method='sha256')
            new_user = User(public_id=public_id,
                            password=hashed_password,
                            name=form.username.data, email=form.email.data, register_date=datetime.datetime.now())
            db.session.add(new_user)
            db.session.commit()
            token = token_encode(public_id)
            sendEmail.confirmationMail(
                to=form.email.data, body=f'{website}/confirm?token={token}', userName=form.username.data)
            flash("User was created and you will get a mail to confirm your account.")
        if email is not None or username is not None:
            flash("Email or username is exist!")
    return render_template("register.html", form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(name=form.username.data).first()
        if not user:
            flash("That User Doesn't Exist! Try Again...")
        elif not user.confirmed:
            flash('The account is not confirmed.')
        elif check_password_hash(user.password, form.password.data):
            token = jwt.encode({'public_id': user.public_id, 'exp': datetime.datetime.utcnow(
            ) + datetime.timedelta(minutes=300)}, app.config['SECRET_KEY'], 'HS256')
            session['token'] = token
            return redirect(url_for('home'))
        elif not check_password_hash(user.password, form.password.data):
            flash('Wrong password. Please try again.')
    return render_template('login.html', form=form)


@app.route('/confirm', methods=['GET'])
@token_required
def confirm(current_user):
    user = User.query.filter(User.email == current_user.email).first()
    if user.confirmed:
        flash('Account already confirmed!')
    else:
        user.confirmed = True
        user.confirmed_on = datetime.datetime.now()
        db.session.commit()
        flash('You have confirmed your account. Thanks!')
    return render_template('home.html', current_user=current_user)


@app.route('/logout')
@token_required
def logout(current_user):
    session.clear()
    return redirect(url_for('login'))


@app.route('/')
@app.route('/home')
@token_required
def home(current_user):
    return render_template('home.html', current_user=current_user)


@app.route('/create', methods=['GET', 'POST'])
@admin_control
def create(current_user):
    form = UploadForm()
    result = []
    if current_user.admin:
        if form.validate_on_submit():
            for file in form.file.data:
                filename = secure_filename(file.filename)
                if allowed_file(filename):
                    try:
                        file_type = extract.file_type(filename)
                        if file_type == 'csv':
                            df = extract.reading_csv_files(file)
                        elif file_type == 'json':
                            df = extract.reading_json_files(file) 
                        df = extract.df_arrange(df, filename)
                        df['user_id'] = current_user.id
                        df.to_sql(con=db.engine, name='nasdaq',
                                index=False, if_exists='append')
                        result.append({'filename': filename,
                                    'success': True})
                        flash(f"{filename} was added successfully!")
                    except:
                
                        flash(f"{filename} could not be added!")
                        result.append({'filename': filename,
                                    'success': False, 'reason': 'The file is not proper for db.'})
                else:
                    flash(f"{filename} type is not supported!")
                    result.append({'filename': filename,
                                   'success': False, 'reason': 'File type is not supported!'})

            sendEmail.emailSendForFile(to=current_user.email,
                                       body=result, userName=current_user.name)
            return render_template('create.html', form=form, current_user=current_user)
    return render_template('create.html', form=form, current_user=current_user)

@app.route('/download', methods=['GET', 'POST'])
@token_required
def download(current_user, name=''):
    form = SelectForm()
    column_names = Nasdaq.query.with_entities(db.distinct(Nasdaq.name)).all()
    column_names = [col[0] for col in column_names]
    form.file_name.choices = column_names
    form.file_type.choices = list(ALLOWED_EXTENSIONS)
    if form.validate_on_submit():
        data_all = Nasdaq.query.filter(
            Nasdaq.name == form.file_name.data).order_by(Nasdaq.date).all()
        if form.file_type.data == 'csv':
            result = extract.download_csv_nasdaq(data_all)
            response = extract.file_download(
                form.file_name.data, result, form.file_type.data)
        elif form.file_type.data == 'json':
            result = extract.download_json_nasdaq(data_all)
            response = extract.file_download(
                form.file_name.data, result, form.file_type.data)
        return response
    return render_template('download.html', form=form, current_user=current_user)


@app.route('/datapage', methods=['GET', 'POST'])
@token_required
def datapage(current_user):
    form_get = DataForm()
    column_names = Nasdaq.query.with_entities(db.distinct(Nasdaq.name)).all()
    column_names = [col[0] for col in column_names]
    form_get.file_name.choices = column_names
    rows = ''
    if form_get.validate_on_submit():
        rows = Nasdaq.query.filter(
            Nasdaq.name == form_get.file_name.data,
            Nasdaq.date >= form_get.start_date.data,
            Nasdaq.date <= form_get.end_date.data
        ).order_by(Nasdaq.date).all()

    return render_template('datapage.html', form_get=form_get, current_user=current_user, rows=rows)


@app.route('/userprofile', methods=['GET', 'POST'])
@token_required
def userprofile(current_user):
    form = UpdateForm()
    user = User.query.get_or_404(current_user.id)
    form.username.default = current_user.name

    if form.validate_on_submit():
        if check_password_hash(current_user.password, form.password_hash.data):
            new_username_attempt = User.query.filter(
                User.name == form.username.data).first()
            if new_username_attempt is not None:
                flash('Please choose another username!')
            elif new_username_attempt is None:
                user.username = form.username.data
                db.session.commit()
                flash("Username was updated successfully!")
                sendEmail.updateUsername(
                    to=current_user.email, userName=user.username, previousUsername=current_user.username)
    form.process()
    return render_template('userprofile.html', current_user=current_user, form=form)

@app.route('/beadmin', methods = ['GET', 'POST'])
@token_required
def beadmin(current_user):
    current_user.admin=1
    db.session.commit()
    return render_template('home.html', current_user=current_user)

@app.route('/beuser', methods = ['GET', 'POST'])
@token_required
def beuser(current_user):
    current_user.admin=0
    db.session.commit()
    return render_template('home.html', current_user=current_user)


@app.errorhandler(401)
def page_not_found(e):
    return render_template("401.html"), 401


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def page_not_found(e):
    return render_template("500.html"), 500