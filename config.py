import os

# ===== App Secrets (REPLACE IN PRODUCTION) =====
SECRET_KEY = os.environ.get("APP_SECRET_KEY", "I264Cb-mBNrf4Cj8I5AGVSRTGYQqbcbCh45Odvq7jq0")
FERNET_KEY = os.environ.get("APP_FERNET_KEY", "LXlCMzAq_iJbOlgTiIAWLZ04oM0hElRQUs1eihli1ME=")  # base64 urlsafe 32-byte key

# ===== Oracle (backend) connection for this web app's data store =====
# Use either a single DSN string like "host:1521/service" or a TNS alias if using Thick mode
ORACLE_APP_USER = os.environ.get("APP_DB_USER", "APP_USER")
ORACLE_APP_PASSWORD = os.environ.get("APP_DB_PASSWORD", "CHANGE_ME")
ORACLE_APP_DSN = os.environ.get("APP_DB_DSN", "localhost:1521/XEPDB1")
ORACLE_APP_MODE = os.environ.get("APP_DB_MODE", "thin")  # 'thin' or 'thick'

# ===== Email (SMTP) Settings =====
SMTP_SERVER = os.environ.get("SMTP_SERVER", "localhost")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "25"))
SMTP_USE_TLS = bool(int(os.environ.get("SMTP_USE_TLS", "0")))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")

# ===== Misc =====
SQLCMD_PATH = os.environ.get("SQLCMD_PATH", "sqlcmd")  # path to sqlcmd.exe if not in PATH
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "no-reply@healthcheck.local")
