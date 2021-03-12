from flask import Flask, url_for, render_template, request, session, abort, redirect, jsonify
from io import BytesIO
import datetime
from data import db_session
from werkzeug.security import generate_password_hash, check_password_hash
import db_additions
import utils
from auth_forms import LoginForm, RegisterForm


app = Flask(__name__)
app.config["SECRET_KEY"] = "qazwsxedcrfv"


@app.route('/')
def index():
    if 'user' in session:
        user = db_additions.get_user(int(session['user']))
        return render_template("index.html", user=user)
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user' in session:
        return redirect('/')
    form = LoginForm()
    
    if form.validate_on_submit():
        print(request.form)
        return redirect('/login')
    return render_template('login.html', title='Вход', form=form)

@app.route('/register', methods=["GET", "POST"])
def register():
    if 'user' in session:
        return redirect('/')
    
    form = RegisterForm()
    if form.validate_on_submit():
        name = request.form.get('username')
        login = request.form.get('login')
        hashed_password = generate_password_hash(request.form.get('password'))

        if not utils.check_email(request.form['email']):
            return render_template('register.html', title='Регистрация', form=form, errors="Неправильный формат почты.")
        email = request.form.get('email')
        user = db_additions.register_user(login, hashed_password, email, name)
        session['user'] = user.id
        session['role'] = user.role
        return redirect('/')
    return render_template('register.html', title='Регистрация', form=form)

@app.route('/logout')
def logout():
    if 'user' not in session:
        return redirect('/login')
    session.pop('user')
    session.pop('role')
    return redirect('/login')



if __name__ == '__main__':
    db_session.global_init('db/db.sqlite')
    db = db_session.create_session()
    app.run('127.0.0.1', port=8080, debug=True)
