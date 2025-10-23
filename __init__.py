from flask import Flask
import oracledb
from . import db
from .security import init_crypto

def create_app():
    app = Flask(__name__)
    app.config.from_object('config')

    # init crypto helpers
    init_crypto(app.config['FERNET_KEY'])

    # configure python-oracledb mode for app's Oracle backend
    mode = app.config.get('ORACLE_APP_MODE', 'thin').lower()
    if mode == 'thick':
        # If thick mode needed, ensure Oracle Client libraries are available.
        # Optionally: oracledb.init_oracle_client()
        pass

    # init DB pool for app backend
    db.init_app(app)

    # register blueprints
    from .auth import auth_bp
    from .admin import admin_bp
    from .oracle_module import oracle_bp
    from .sqlserver_module import sqlserver_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(oracle_bp, url_prefix='/oracle')
    app.register_blueprint(sqlserver_bp, url_prefix='/sqlserver')

    @app.route('/')
    def index():
        from flask import redirect, url_for, session
        if session.get('user_id'):
            return redirect(url_for('oracle.list_targets'))
        return redirect(url_for('auth.login'))

    return app
