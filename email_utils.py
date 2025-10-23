import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
from flask import current_app

def send_email(to_email: str, subject: str, html_body: str):
    cfg = current_app.config
    msg = MIMEText(html_body, 'html')
    msg['Subject'] = subject
    msg['From'] = formataddr(('HealthCheck', cfg['DEFAULT_FROM_EMAIL']))
    msg['To'] = to_email

    server = cfg['SMTP_SERVER']
    port = cfg['SMTP_PORT']
    use_tls = cfg['SMTP_USE_TLS']
    username = cfg['SMTP_USERNAME']
    password = cfg['SMTP_PASSWORD']

    with smtplib.SMTP(server, port) as s:
        if use_tls:
            s.starttls()
        if username:
            s.login(username, password)
        s.sendmail(msg['From'], [to_email], msg.as_string())
