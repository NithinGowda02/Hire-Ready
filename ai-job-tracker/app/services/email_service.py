# app/services/email_service.py
#
# Sends transactional emails via Flask-Mail (Gmail SMTP).
# Requires these env vars on Render:
#   MAIL_SERVER   = smtp.gmail.com
#   MAIL_PORT     = 587
#   MAIL_USE_TLS  = true
#   MAIL_USERNAME = careerai.noreply@gmail.com
#   MAIL_PASSWORD = <16-char Gmail app password>

from __future__ import annotations

import logging
from flask         import current_app
from flask_mail    import Mail, Message

logger = logging.getLogger(__name__)

# Mail instance — shared with __init__.py via init_mail()
mail = Mail()


def init_mail(app) -> None:
    """Call this from create_app() after app.config is loaded."""
    mail.init_app(app)


def send_email(to: str, subject: str, body: str, html: str | None = None) -> bool:
    """
    Send a plain-text (+ optional HTML) email.

    Returns True on success, False on failure.
    Never raises — logs the error instead so the caller can degrade gracefully.
    """
    if not current_app.config.get('MAIL_USERNAME'):
        logger.warning('[mail] MAIL_USERNAME not configured — email not sent.')
        return False

    if current_app.config.get('MAIL_SUPPRESS_SEND'):
        logger.info('[mail] MAIL_SUPPRESS_SEND=true — skipping send to %s', to)
        return True

    try:
        msg = Message(
            subject   = subject,
            recipients = [to],
            body      = body,
            html      = html,
        )
        mail.send(msg)
        logger.info('[mail] ✓ Sent "%s" to %s', subject, to)
        return True

    except Exception:
        logger.exception('[mail] ✗ Failed to send "%s" to %s', subject, to)
        return False


def send_password_reset_email(user_name: str, user_email: str, reset_link: str, expires_minutes: int = 60) -> bool:
    """Convenience wrapper specifically for password reset emails."""
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