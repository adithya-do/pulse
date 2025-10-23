from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from functools import wraps
from . import db
from .security import enc, dec
import datetime as dt
import oracledb

oracle_bp = Blueprint('oracle', __name__)

def login_required(f):
    @wraps(f)
    def _wrap(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return _wrap

def require_super_or_admin(f):
    @wraps(f)
    def _wrap(*args, **kwargs):
        if session.get('role') not in ('ADMIN','SUPER'):
            # In future: check module-specific permission mapping
            pass
        return f(*args, **kwargs)
    return _wrap

@oracle_bp.route('/targets')
@login_required
def list_targets():
    rows = db.query_all("""
        SELECT target_id, s_no, db_name, environment, host, db_version, method, status, last_check, check_status, error_msg
        FROM oracle_targets ORDER BY s_no
    """)
    return render_template('oracle/list.html', targets=rows)

@oracle_bp.route('/target/new', methods=['GET','POST'])
@login_required
@require_super_or_admin
def target_new():
    if request.method == 'POST':
        p = {k: request.form.get(k) for k in request.form.keys()}
        p['common_password_enc'] = enc(p.get('common_password','')).decode()
        p['is_active'] = 1 if request.form.get('is_active') == 'on' else 0
        db.exec_sql("""
            INSERT INTO oracle_targets(target_id, s_no, db_name, environment, host, db_version, method, tns_alias, host_name, port, service_name, common_user, common_password_enc, status, is_active)
            VALUES (oracle_targets_seq.NEXTVAL, :s_no, :db_name, :environment, :host, :db_version, :method, :tns_alias, :host_name, :port, :service_name, :common_user, :common_password_enc, 'UNKNOWN', :is_active)
        """, p)
        flash('Target added.', 'success')
        return redirect(url_for('oracle.list_targets'))
    return render_template('oracle/edit.html', target=None)

@oracle_bp.route('/target/<int:tid>/edit', methods=['GET','POST'])
@login_required
@require_super_or_admin
def target_edit(tid):
    if request.method == 'POST':
        p = {k: request.form.get(k) for k in request.form.keys()}
        if request.form.get('common_password'):
            p['common_password_enc'] = enc(p.get('common_password','')).decode()
            db.exec_sql("""
                UPDATE oracle_targets SET s_no=:s_no, db_name=:db_name, environment=:environment, host=:host, db_version=:db_version,
                method=:method, tns_alias=:tns_alias, host_name=:host_name, port=:port, service_name=:service_name, common_user=:common_user,
                common_password_enc=:common_password_enc, is_active=:is_active WHERE target_id=:tid
            """, {**p, 'tid': tid, 'is_active': 1 if request.form.get('is_active')=='on' else 0})
        else:
            db.exec_sql("""
                UPDATE oracle_targets SET s_no=:s_no, db_name=:db_name, environment=:environment, host=:host, db_version=:db_version,
                method=:method, tns_alias=:tns_alias, host_name=:host_name, port=:port, service_name=:service_name, common_user=:common_user,
                is_active=:is_active WHERE target_id=:tid
            """, {**p, 'tid': tid, 'is_active': 1 if request.form.get('is_active')=='on' else 0})
        flash('Target updated.', 'success')
        return redirect(url_for('oracle.list_targets'))
    t = db.query_all("""SELECT * FROM oracle_targets WHERE target_id=:tid""", {'tid': tid})
    if not t:
        flash('Target not found', 'danger')
        return redirect(url_for('oracle.list_targets'))
    target = t[0]
    try:
        target['common_password'] = dec(target['COMMON_PASSWORD_ENC'])
    except Exception:
        target['common_password'] = ''
    return render_template('oracle/edit.html', target=target)

@oracle_bp.route('/target/<int:tid>/check', methods=['POST'])
@login_required
def run_check(tid):
    t = db.query_all("""SELECT * FROM oracle_targets WHERE target_id=:tid""", {'tid': tid})
    if not t:
        flash('Target not found', 'danger')
        return redirect(url_for('oracle.list_targets'))
    t = t[0]
    db.exec_sql("""UPDATE oracle_targets SET check_status='InProgress', last_check = SYSDATE, error_msg=NULL WHERE target_id=:tid""", {'tid': tid})
    try:
        result = perform_health_check(t)
        db.exec_sql("""
            INSERT INTO oracle_checks(check_id, target_id, instance_status, db_open_mode, worst_tbs_pct, tablespaces_online, last_full_backup, last_arch_backup, started_at, completed_at, status, error_msg)
            VALUES (oracle_checks_seq.NEXTVAL, :target_id, :instance_status, :db_open_mode, :worst_tbs_pct, :tablespaces_online, :last_full_backup, :last_arch_backup, :started_at, :completed_at, :status, :error_msg)
        """, result)
        db.exec_sql("""
            UPDATE oracle_targets SET status=:status, last_check=:completed_at, check_status='Completed', error_msg=:error_msg WHERE target_id=:target_id
        """, result)
        flash('Check completed.', 'success')
    except Exception as e:
        db.exec_sql("""UPDATE oracle_targets SET check_status='Completed', error_msg=:e WHERE target_id=:tid""", {'e': str(e), 'tid': tid})
        flash('Check failed: %s' % e, 'danger')
    return redirect(url_for('oracle.list_targets'))

def perform_health_check(t):
    method = t['METHOD']
    user = t['COMMON_USER']
    pw = dec(t['COMMON_PASSWORD_ENC'])
    dsn = None
    mode = 'thin'
    if method == 'TNS':
        # Use Thick mode with TNS alias
        oracledb.init_oracle_client()  # Require client libraries installed on server
        mode = 'thick'
        dsn = t['TNS_ALIAS']
    else:
        # THIN mode
        host = t['HOST_NAME']
        port = int(t['PORT'])
        svc  = t['SERVICE_NAME']
        dsn = f"{host}:{port}/{svc}"

    # connect to target DB
    con = oracledb.connect(user=user, password=pw, dsn=dsn)
    cur = con.cursor()

    # metrics
    cur.execute("SELECT STATUS FROM v$instance"); inst_status = cur.fetchone()[0]
    cur.execute("SELECT OPEN_MODE FROM v$database"); open_mode = cur.fetchone()[0]

    # worst tablespace %
    try:
        cur.execute("SELECT NVL(MAX(used_percent),0) FROM dba_tablespace_usage_metrics")
        worst_pct = float(cur.fetchone()[0])
    except Exception:
        # fallback calculation
        cur.execute("""
            SELECT MAX( ROUND( ( (df.bytes - NVL(fs.bytes,0)) / df.bytes) * 100, 2) ) AS used_pct
            FROM (SELECT tablespace_name, SUM(bytes) bytes FROM dba_data_files GROUP BY tablespace_name) df
            LEFT JOIN (SELECT tablespace_name, SUM(bytes) bytes FROM dba_free_space GROUP BY tablespace_name) fs
            ON df.tablespace_name = fs.tablespace_name
        """)
        worst_pct = float(cur.fetchone()[0] or 0)

    # tablespaces online (1=yes if all ONLINE)
    cur.execute("SELECT COUNT(*) FROM dba_tablespaces WHERE status <> 'ONLINE'")
    offline_count = int(cur.fetchone()[0])
    ts_online = 1 if offline_count == 0 else 0

    # backups (requires privileges)
    last_full = None
    last_arch = None
    try:
        cur.execute("SELECT MAX(end_time) FROM V$RMAN_BACKUP_JOB_DETAILS WHERE INPUT_TYPE='DB FULL' AND STATUS='COMPLETED'")
        last_full = cur.fetchone()[0]
    except Exception:
        pass
    try:
        cur.execute("SELECT MAX(end_time) FROM V$RMAN_BACKUP_JOB_DETAILS WHERE INPUT_TYPE='ARCHIVELOG' AND STATUS='COMPLETED'")
        last_arch = cur.fetchone()[0]
    except Exception:
        pass

    cur.close(); con.close()

    status = 'OK' if (inst_status=='OPEN' or inst_status=='MOUNTED' or inst_status=='STARTED') and (open_mode in ('READ WRITE','READ ONLY','MOUNTED')) else 'ISSUE'
    now = dt.datetime.now()
    return {
        'target_id': t['TARGET_ID'],
        'instance_status': inst_status,
        'db_open_mode': open_mode,
        'worst_tbs_pct': worst_pct,
        'tablespaces_online': ts_online,
        'last_full_backup': last_full,
        'last_arch_backup': last_arch,
        'started_at': now,
        'completed_at': now,
        'status': status,
        'error_msg': None
    }
