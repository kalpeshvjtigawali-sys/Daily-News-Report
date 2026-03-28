#!/usr/bin/env python3
"""
Sends the email-safe report as the email body via Gmail SMTP.
Requires env vars: GMAIL_USER, GMAIL_APP_PASSWORD, RECIPIENT_EMAIL
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

def main():
    gmail_user     = os.environ.get('GMAIL_USER', '').strip()
    gmail_password = os.environ.get('GMAIL_APP_PASSWORD', '').strip()
    recipient      = os.environ.get('RECIPIENT_EMAIL', '').strip()

    if not gmail_user or not gmail_password or not recipient:
        print("⚠️  Email secrets not configured — skipping email. "
              "Add GMAIL_USER, GMAIL_APP_PASSWORD, RECIPIENT_EMAIL as GitHub Secrets to enable.")
        return

    # Use email-safe version (inline styles, table layout)
    today = datetime.now(IST).strftime('%Y-%m-%d')
    email_path = f'reports/email_{today}.html'
    if not os.path.exists(email_path):
        email_path = 'reports/email_latest.html'
    if not os.path.exists(email_path):
        # Fall back to web report
        email_path = f'reports/report_{today}.html'
    if not os.path.exists(email_path):
        email_path = 'reports/latest.html'
    if not os.path.exists(email_path):
        print("❌ No report file found. Skipping email.")
        return

    with open(email_path, 'r', encoding='utf-8') as f:
        html_body = f.read()

    date_display = datetime.now(IST).strftime('%d %B %Y')
    subject = f"☀️ Solar & Renewable Energy India — Daily Report | {date_display}"

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From']    = f"Daily News Report <{gmail_user}>"
    msg['To']      = recipient

    plain = (
        f"Solar & Renewable Energy India — Daily Report\n"
        f"Date: {date_display}\n\n"
        f"View the full report online:\n"
        f"https://kalpeshvjtigawali-sys.github.io/Daily-News-Report/reports/latest.html"
    )
    msg.attach(MIMEText(plain, 'plain'))
    msg.attach(MIMEText(html_body, 'html'))

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, recipient, msg.as_string())

    print(f"✅ Email-safe report sent to {recipient}")

if __name__ == '__main__':
    main()
