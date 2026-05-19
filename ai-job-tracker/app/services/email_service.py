# app/services/email_service.py
#
# Sends email via Brevo HTTP API (not SMTP).
# Render's free tier blocks SMTP port 587, so we use HTTP instead.
#
# Setup:
#   1. Sign up free at https://brevo.com
#   2. Go to SMTP & API → API Keys → Create API Key
#   3. Add to Render environment:
#        BREVO_API_KEY     = your-api-key
#        MAIL_DEFAULT_SENDER = careerai.noreply@gmail.com  (your sender email)

from __future__ import annotations

import logging
import os
import requests

logger = logging.getLogger(__name__)

BREVO_SEND_URL = 'https://api.brevo.com/v3/smtp/email'


def send_email(to: str, subject: str, body: str, html: str | None = None) -> bool:
    """
    Send email via Brevo HTTP API.
    Returns True on success, False on failure. Never raises.
    """
    api_key = os.environ.get('BREVO_API_KEY', '').strip()
    sender  = os.environ.get('MAIL_DEFAULT_SENDER', '').strip()

    if not api_key:
        logger.warning('[mail] BREVO_API_KEY not set — email not sent.')
        return False

    if not sender:
        logger.warning('[mail] MAIL_DEFAULT_SENDER not set — email not sent.')
        return False

    payload = {
        'sender':     {'email': sender, 'name': 'CareerAI'},
        'to':         [{'email': to}],
        'subject':    subject,
        'textContent': body,
    }
    if html:
        payload['htmlContent'] = html

    try:
        resp = requests.post(
            BREVO_SEND_URL,
            json=payload,
            headers={
                'api-key':      api_key,
                'Content-Type': 'application/json',
            },
            timeout=15,
        )
        resp.raise_for_status()
        logger.info('[mail] ✓ Sent "%s" to %s', subject, to)
        return True

    except Exception:
        logger.exception('[mail] ✗ Failed to send "%s" to %s', subject, to)
        return False


def send_password_reset_email(
    user_name: str,
    user_email: str,
    reset_link: str,
    expires_minutes: int = 60,
) -> bool:
    """Convenience wrapper for password reset emails."""
    subject = 'Reset your CareerAI password'

    body = (
        f'Hi {user_name},\n\n'
        f'Click the link below to reset your CareerAI password.\n'
        f'This link expires in {expires_minutes} minutes.\n\n'
        f'{reset_link}\n\n'
        f'If you did not request this, you can safely ignore this email.\n\n'
        f'— The CareerAI Team'
    )

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto;padding:32px">
      <h2 style="margin-bottom:4px">Reset your password</h2>
      <p style="color:#555">Hi {user_name},</p>
      <p style="color:#555">
        Click the button below to reset your CareerAI password.<br>
        This link expires in <strong>{expires_minutes} minutes</strong>.
      </p>
      <p style="margin:28px 0">
        <a href="{reset_link}"
           style="background:#111;color:#fff;padding:13px 28px;border-radius:7px;
                  text-decoration:none;font-weight:600;font-size:15px">
          Reset Password
        </a>
      </p>
      <p style="color:#888;font-size:13px">
        If you didn't request this, you can safely ignore this email.<br>
        Your password won't change until you click the link above.
      </p>
      <hr style="border:none;border-top:1px solid #eee;margin:24px 0">
      <p style="color:#aaa;font-size:12px">— The CareerAI Team</p>
    </div>
    """

    return send_email(user_email, subject, body, html)