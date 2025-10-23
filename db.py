import oracledb
from flask import current_app, g
import threading

_pool_lock = threading.Lock()

def _get_pool():
    if 'db_pool' not in g:
        cfg = current_app.config
        user = cfg['ORACLE_APP_USER']
        pw = cfg['ORACLE_APP_PASSWORD']
        dsn = cfg['ORACLE_APP_DSN']
        mode = cfg.get('ORACLE_APP_MODE','thin').lower()
        if mode == 'thick':
            oracledb.init_oracle_client()  # expects client libs in default location / PATH
        with _pool_lock:
            g.db_pool = oracledb.create_pool(user=user, password=pw, dsn=dsn, min=1, max=5, increment=1)
    return g.db_pool

def get_conn():
    pool = _get_pool()
    return pool.acquire()

def close_pool(e=None):
    pool = g.pop('db_pool', None)
    if pool:
        pool.close()

def init_app(app):
    app.teardown_appcontext(close_pool)

def query_one(sql, params=None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or {})
            return cur.fetchone()

def query_all(sql, params=None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or {})
            cols = [d[0] for d in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
            return rows

def exec_sql(sql, params=None, commit=True):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or {})
        if commit:
            conn.commit()
