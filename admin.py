from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from functools import wraps
from . import db
from .security import hash_password

admin_bp = Blueprint('admin', __name__)

def require_admin(f):
    @wraps(f)
    def _wrap(*args, **kwargs):
        if session.get('role') not in ('ADMIN','SUPER'):
            flash('Admin privileges required.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return _wrap

@admin_bp.route('/')
@require_admin
def dashboard():
    users = db.query_all("""SELECT user_id, login_id, full_name, email, role, active FROM users ORDER BY user_id""")
    return render_template('admin/users.html', users=users)

@admin_bp.route('/user/new', methods=['GET','POST'])
@require_admin
def user_new():
    if request.method == 'POST':
        login_id = request.form['login_id'].strip()
        full_name = request.form['full_name'].strip()
        email = request.form['email'].strip()
        role = request.form['role']
        active = 1 if request.form.get('active') == 'on' else 0
        password_hash = hash_password(request.form['password'])
        db.exec_sql("""
            INSERT INTO users(user_id, login_id, full_name, email, role, password_hash, active)
            VALUES (users_seq.NEXTVAL, :login_id, :full_name, :email, :role, :password_hash, :active)
        """, {'login_id': login_id, 'full_name': full_name, 'email': email, 'role': role, 'password_hash': password_hash, 'active': active})
        flash('User created.', 'success')
        return redirect(url_for('admin.dashboard'))
    return render_template('admin/user_edit.html', user=None)

@admin_bp.route('/user/<int:uid>/edit', methods=['GET','POST'])
@require_admin
def user_edit(uid):
    if request.method == 'POST':
        full_name = request.form['full_name'].strip()
        email = request.form['email'].strip()
        role = request.form['role']
        active = 1 if request.form.get('active') == 'on' else 0
        if request.form.get('password'):
            db.exec_sql("""UPDATE users SET full_name=:full_name, email=:email, role=:role, active=:active, password_hash=:ph WHERE user_id=:uid""",
                        {'full_name': full_name, 'email': email, 'role': role, 'active': active, 'ph': hash_password(request.form['password']), 'uid': uid})
        else:
            db.exec_sql("""UPDATE users SET full_name=:full_name, email=:email, role=:role, active=:active WHERE user_id=:uid""" ,
                        {'full_name': full_name, 'email': email, 'role': role, 'active': active, 'uid': uid})
        flash('User updated.', 'success')
        return redirect(url_for('admin.dashboard'))
    user = db.query_all("""SELECT user_id, login_id, full_name, email, role, active FROM users WHERE user_id=:uid""", {'uid': uid})
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('admin.dashboard'))
    return render_template('admin/user_edit.html', user=user[0])
