"""Transactional mail — password reset etc. Logs when SMTP not configured."""

from __future__ import annotations

import logging
import smtplib
from email.mime.text import MIMEText

from tools.tools import getEnvConfig

logger = logging.getLogger(__name__)


def send_mail(to_email: str, subject: str, body: str) -> dict:
    host = (getEnvConfig('SMTP_HOST') or '').strip()
    port = int(getEnvConfig('SMTP_PORT') or 587)
    user = (getEnvConfig('SMTP_USER') or '').strip()
    password = (getEnvConfig('SMTP_PASSWORD') or '').strip()
    from_addr = (getEnvConfig('SMTP_FROM') or user or 'noreply@spark.app').strip()
    if not host or not to_email:
        logger.info('mail.mock to=%s subject=%s body=%s', to_email, subject, body[:200])
        return {'ok': True, 'mock': True}
    try:
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = from_addr
        msg['To'] = to_email
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            smtp.starttls()
            if user and password:
                smtp.login(user, password)
            smtp.sendmail(from_addr, [to_email], msg.as_string())
        return {'ok': True, 'mock': False}
    except Exception as exc:
        logger.exception('smtp send failed')
        return {'ok': False, 'error': str(exc)[:300]}
