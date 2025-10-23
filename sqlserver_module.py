from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from functools import wraps
from . import db
from .security import enc, dec
import subprocess, shlex

sqlserver_bp = Blueprint('sqlserver', __name__)

def login_required(f):
    @wraps(f)
    def _wrap(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return _wrap

@sqlserver_bp.route('/targets')
@login_required
def list_targets():
    rows = db.query_all("""
        SELECT target_id, s_no, instance_name, environment, host, version, auth_mode, status, last_check, check_status, error_msg
        FROM sqlserver_targets ORDER BY s_no
    """)
    return render_template('sqlserver/list.html', targets=rows)

@sqlserver_bp.route('/target/new', methods=['GET','POST'])
@login_required
def target_new():
    if request.method == 'POST':
        p = {k: request.form.get(k) for k in request.form.keys()}
        if p.get('password'):
            p['password_enc'] = enc(p.get('password','')).decode()
        p['is_active'] = 1 if request.form.get('is_active') == 'on' else 0
        db.exec_sql("""
            INSERT INTO sqlserver_targets(target_id, s_no, instance_name, environment, host, version, auth_mode, username, password_enc, domain, status, is_active)
            VALUES (sqlserver_targets_seq.NEXTVAL, :s_no, :instance_name, :environment, :host, :version, :auth_mode, :username, :password_enc, :domain, 'UNKNOWN', :is_active)
        """, p)
        flash('SQL Server target added.', 'success')
        return redirect(url_for('sqlserver.list_targets'))
    return render_template('sqlserver/edit.html', target=None)

@sqlserver_bp.route('/target/<int:tid>/edit', methods=['GET','POST'])
@login_required
def target_edit(tid):
    if request.method == 'POST':
        p = {k: request.form.get(k) for k in request.form.keys()}
        if request.form.get('password'):
            p['password_enc'] = enc(p.get('password','')).decode()
            db.exec_sql("""
                UPDATE sqlserver_targets SET s_no=:s_no, instance_name=:instance_name, environment=:environment, host=:host, version=:version,
                auth_mode=:auth_mode, username=:username, password_enc=:password_enc, domain=:domain, is_active=:is_active WHERE target_id=:tid
            """, {**p, 'tid': tid, 'is_active': 1 if request.form.get('is_active')=='on' else 0})
        else:
            db.exec_sql("""
                UPDATE sqlserver_targets SET s_no=:s_no, instance_name=:instance_name, environment=:environment, host=:host, version=:version,
                auth_mode=:auth_mode, username=:username, domain=:domain, is_active=:is_active WHERE target_id=:tid
            """, {**p, 'tid': tid, 'is_active': 1 if request.form.get('is_active')=='on' else 0})
        flash('SQL Server target updated.', 'success')
        return redirect(url_for('sqlserver.list_targets'))
    t = db.query_all("""SELECT * FROM sqlserver_targets WHERE target_id=:tid""", {'tid': tid})
    if not t:
        flash('Target not found', 'danger')
        return redirect(url_for('sqlserver.list_targets'))
    target = t[0]
    try:
        target['password'] = dec(target['PASSWORD_ENC'])
    except Exception:
        target['password'] = ''
    return render_template('sqlserver/edit.html', target=target)

@sqlserver_bp.route('/target/<int:tid>/check', methods=['POST'])
@login_required
def run_check(tid):
    t = db.query_all("""SELECT * FROM sqlserver_targets WHERE target_id=:tid""", {'tid': tid})
    if not t:
        flash('Target not found', 'danger')
        return redirect(url_for('sqlserver.list_targets'))
    t = t[0]
    db.exec_sql("""UPDATE sqlserver_targets SET check_status='InProgress', last_check = SYSDATE, error_msg=NULL WHERE target_id=:tid""", {'tid': tid})
    try:
        ok, out = perform_check_sqlcmd(t)
        status = 'OK' if ok else 'ISSUE'
        db.exec_sql("""
            INSERT INTO sqlserver_checks(check_id, target_id, status_text, started_at, completed_at, status, error_msg)
            VALUES (sqlserver_checks_seq.NEXTVAL, :target_id, :status_text, SYSDATE, SYSDATE, :status, :error_msg)
        """, {'target_id': t['TARGET_ID'], 'status_text': out[:4000], 'status': status, 'error_msg': None if ok else out[:4000]})
        db.exec_sql("""UPDATE sqlserver_targets SET status=:status, check_status='Completed', error_msg=:err WHERE target_id=:tid""",
                    {'status': status, 'err': None if ok else out[:4000], 'tid': t['TARGET_ID']})
        flash('Check completed.', 'success' if ok else 'warning')
    except Exception as e:
        db.exec_sql("""UPDATE sqlserver_targets SET check_status='Completed', error_msg=:e WHERE target_id=:tid""", {'e': str(e), 'tid': tid})
        flash('Check failed: %s' % e, 'danger')
    return redirect(url_for('sqlserver.list_targets'))

def perform_check_sqlcmd(t):
    sqlcmd = current_app.config['SQLCMD_PATH']
    instance = t['INSTANCE_NAME']
    auth = t['AUTH_MODE']
    if auth == 'WINDOWS':
        cmd = f'"{sqlcmd}" -S {instance} -E -b -Q "SELECT GETDATE() as now; SELECT @@VERSION as version;"'
    else:
        user = t['USERNAME']
        pw = dec(t['PASSWORD_ENC'])
        cmd = f'"{sqlcmd}" -S {instance} -U {shlex.quote(user)} -P {shlex.quote(pw)} -b -Q "SELECT GETDATE() as now; SELECT @@VERSION as version;"'
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=30)
        ok = (res.returncode == 0)
        out = res.stdout if ok else (res.stderr or res.stdout)
        return ok, out
    except Exception as e:
        return False, str(e)
