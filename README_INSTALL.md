# IIS + Python Health Check Web App (Oracle backend)

This is a starter kit for an IIS-hosted Python (Flask) web application whose backend database is **Oracle**.
It includes:
- Login with roles (**ADMIN**, **SUPER**, **USER**) and bcrypt-hashed passwords
- Forgot-password workflow (emails a **temporary** password)
- Admin console to create users
- Oracle module (add/edit targets, run health checks using **TNS (Thick)** or **THIN** mode)
- SQL Server module (add/edit targets, connectivity check using **sqlcmd**)

> **Note:** Each module uses its own tables in the Oracle backend schema.

---

## 1) Prereqs on Windows Server (IIS)

1. Install Python 3.10+ (x64). Add to PATH.
2. Install IIS with CGI + FastCGI features enabled.
3. Install `wfastcgi` for Python:
   ```bash
   pip install wfastcgi
   wfastcgi-enable  # registers FastCGI on IIS
   ```
4. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```
5. For Oracle Thick (TNS) mode checks, install **Oracle Instant Client** (Basic) and ensure its BIN directory is on PATH.
6. Ensure `sqlcmd` is installed for the SQL Server module (part of MS Command Line Utilities). Point `SQLCMD_PATH` env var if needed.

---

## 2) Configure site in IIS

- Point the website's **physical path** to this project folder.
- Edit `web.config`:
  Replace `|PYTHON|` with the full path to `python.exe` and `|WFASTCGI|` with the path to `wfastcgi.py` in your site-packages.
  Replace `|PORT|` with an available port (e.g., `5000`).
- Make sure the Application Pool identity has the necessary permissions to read this folder and (if using Windows auth for SQL Server) to connect to SQL Server.

---

## 3) Create schema in Oracle

Connect to your Oracle backend as the app schema owner and run:
```sql
@db_init.sql
```
Then create an initial ADMIN user:
```sql
INSERT INTO users(user_id, login_id, full_name, email, role, password_hash, active)
VALUES (users_seq.nextval, 'admin', 'Administrator', 'admin@example.com', 'ADMIN',
        '$2b$12$K1x4qWm9k5QH0pqcX9a6sOOeYxS6Wg2a2C.7uS0mA8qgYx2N0b5tC', 1);
-- The above hash corresponds to password: Admin@123  (Change immediately)
COMMIT;
```

Set environment variables (or edit `config.py`) for the app to connect to the Oracle backend:
```
APP_DB_USER=APP_USER
APP_DB_PASSWORD=***
APP_DB_DSN=host:1521/service
APP_DB_MODE=thin   # or thick (requires Instant Client)
APP_SECRET_KEY=***
APP_FERNET_KEY=***  # must be a base64 urlsafe 32-byte key
SMTP_SERVER=your.smtp.server
SMTP_PORT=25
SMTP_USERNAME=optional
SMTP_PASSWORD=optional
SQLCMD_PATH=C:\Program Files\Microsoft SQL Server\Client SDK\ODBC\170\Tools\Binn\sqlcmd.exe
```

---

## 4) Running locally (optional)

```bash
set FLASK_APP=app.app:application
python -m flask run
```

---

## 5) Notes

- Oracle target checks query: `v$instance`, `v$database`, `dba_tablespace_usage_metrics`, `dba_tablespaces`, and `V$RMAN_BACKUP_JOB_DETAILS`.
  Ensure the **Common User** has read privileges on these views.
- Passwords for **application users** are **bcrypt-hashed**.
- Stored **connection passwords** (for target systems) are encrypted with **Fernet**. Keep `FERNET_KEY` safe.
- SQL Server Windows-auth checks run as the **App Pool identity**; ensure it has access on the SQL Server instance.
