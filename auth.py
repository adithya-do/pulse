from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from . import db
from .security import verify_password, hash_password
from .email_utils import send_email
import secrets

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        login_id = request.form['login_id'].strip()
        password = request.form['password']
        row = db.query_one("""
            SELECT user_id, login_id, full_name, email, role, password_hash, active
            FROM users WHERE login_id = :login_id
        """, {'login_id': login_id})
        if row and row[-2] == 1:
            _, _, full_name, email, role, pwd_hash, active = row
            if verify_password(password, pwd_hash):
                session['user_id'] = row[0]
                session['login_id'] = login_id
                session['full_name'] = full_name
                session['role'] = role
                flash('Welcome, %s!' % full_name, 'success')
                return redirect(url_for('oracle.list_targets'))
        flash('Invalid credentials or account inactive.', 'danger')
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

@auth_bp.route('/forgot', methods=['GET','POST'])
def forgot():
    if request.method == 'POST':
        login_id = request.form['login_id'].strip()
        row = db.query_one("""SELECT user_id, email FROM users WHERE login_id=:login_id""", {'login_id': login_id})
        if not row:
            return render_template('forgot.html', sent=True)  # Don't reveal existence
        user_id, email = row
        temp_pw = secrets.token_urlsafe(10)
        db.exec_sql("""UPDATE users SET password_hash=:ph WHERE user_id=:uid""", {'ph': hash_password(temp_pw), 'uid': user_id})
        send_email(email, 'Your temporary password',
                   f"""<p>Hello,</p><p>Your temporary password is: <b>{temp_pw}</b></p>
                   <p>Please log in and change it immediately.</p>""" )
        return render_template('forgot.html', sent=True)
    return render_template('forgot.html', sent=False)
