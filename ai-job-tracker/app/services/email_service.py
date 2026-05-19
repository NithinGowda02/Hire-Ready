import smtplib
from email.message import EmailMessage

from flask import current_app


def send_email(recipient: str, subject: str, body: str) -> bool:
    if current_app.config.get('MAIL_SUPPRESS_SEND'):
        current_app.logger.info('Email suppressed for %s with subject %s', recipient, subject)
        current_app.logger.info(body)
        return False

    mail_server = current_app.config.get('MAIL_SERVER')
    sender = current_app.config.get('MAIL_DEFAULT_SENDER')

    if not mail_server or not sender:
        current_app.logger.warning(
            'Email not sent because MAIL_SERVER or MAIL_DEFAULT_SENDER is not configured.'
        )
        current_app.logger.info(body)
        return False

    message = EmailMessage()
    message['Subject'] = subject
    message['From'] = sender
    message['To'] = recipient
    message.set_content(body)

    mail_port = current_app.config.get('MAIL_PORT', 587)
    use_ssl = current_app.config.get('MAIL_USE_SSL', False)
    use_tls = current_app.config.get('MAIL_USE_TLS', True)
    username = current_app.config.get('MAIL_USERNAME')
    password = current_app.config.get('MAIL_PASSWORD')

    smtp_class = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP

    with smtp_class(mail_server, mail_port, timeout=15) as server:
        if not use_ssl and use_tls:
            server.starttls()
        if username and password:
            server.login(username, password)
        server.send_message(message)

    return True
