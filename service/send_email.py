import threading
import logging
import time
import socket
import smtplib
import os
import ssl  
from email.utils import formataddr
from email import message_from_string, policy
from flask_mail import Message
from flask import current_app
from extensions import mail 

logger = logging.getLogger(__name__)

def _send_with_retry(app, msg, recipient_info, retries=2, delay_seconds=1.5):
    """
    Custom sender that uses raw smtplib fallback to guarantee SSL/TLS stability 
    inside background threads. Uses modern send_message to completely avoid ASCII conversion issues.
    """
    last_error = None
    
    smtp_server = app.config.get('MAIL_SERVER', 'mail.privateemail.com')
    smtp_port = int(app.config.get('MAIL_PORT', 465))
    username = app.config.get('MAIL_USERNAME')
    password = app.config.get('MAIL_PASSWORD')
    use_ssl = bool(app.config.get('MAIL_USE_SSL', False))
    use_tls = bool(app.config.get('MAIL_USE_TLS', False))
    mail_timeout = int(app.config.get('MAIL_TIMEOUT', 20))

    # --- FIX: We do NOT convert to string here anymore! ---
    # Prefer a precompiled string attached to the message (set when queuing),
    # otherwise render inside the app context.
    try:
        if hasattr(msg, '_compiled_string'):
            msg_string = msg._compiled_string
        else:
            with app.app_context():
                # Triggering Flask-Mail's internal rendering mechanism to attach HTML formats 
                # safely to the message structure before we drop out of app_context
                msg_string = msg.as_string()
    except Exception as prep_err:
        logger.error("❌ Failed to pre-compile email payload inside app_context: %s", prep_err)
        return False, f"Message compilation error: {str(prep_err)}"

    total_attempts = retries + 1
    for attempt in range(1, total_attempts + 1):
        try:
            ssl_context = ssl.create_default_context()

            if use_ssl or smtp_port == 465:
                server = smtplib.SMTP_SSL(smtp_server, smtp_port, context=ssl_context, timeout=mail_timeout)
            else:
                server = smtplib.SMTP(smtp_server, smtp_port, timeout=mail_timeout)

            with server:
                server.ehlo()
                if use_tls and not use_ssl:
                    server.starttls(context=ssl_context)
                    server.ehlo()

                if username and password:
                    try:
                        server.login(username, password)
                    except smtplib.SMTPException:
                        raise

                # --- FIX: Convert Flask-Mail Message into an EmailMessage then send ---
                # Render the precompiled message to SMTP-safe bytes and send via sendmail.
                try:
                    email_msg = message_from_string(msg_string, policy=policy.SMTP)
                    msg_bytes = email_msg.as_bytes(policy=policy.SMTP)
                    server.sendmail(msg.sender, msg.recipients, msg_bytes)
                except Exception:
                    # Final fallback: normalize line endings and send UTF-8 bytes
                    normalized = msg_string.replace('\r\n', '\n').replace('\n', '\r\n')
                    msg_bytes = normalized.encode('utf-8', errors='replace')
                    server.sendmail(msg.sender, msg.recipients, msg_bytes)

            logger.info("✅ Success: Email delivered to %s", recipient_info)
            return True, "Email sent"
            
        except (ConnectionResetError, BrokenPipeError, socket.timeout, TimeoutError,
                smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError,
                smtplib.SMTPAuthenticationError, OSError, smtplib.SMTPException, UnicodeEncodeError) as exc:
            last_error = exc
            if attempt < total_attempts:
                backoff = delay_seconds * (2 ** (attempt - 1))
                logger.warning(
                    "SMTP transient error for %s (attempt %s/%s): %s. Retrying in %.1fs",
                    recipient_info,
                    attempt,
                    total_attempts,
                    repr(exc),
                    backoff,
                )
                time.sleep(backoff)
                continue
            break

    return False, str(last_error) if last_error else "Unknown SMTP error"

def send_async_email(app, msg, recipient_info):
    """Worker function for the background thread."""
    retries = int(app.config.get('MAIL_RETRY_COUNT', 2))
    delay_seconds = float(app.config.get('MAIL_RETRY_DELAY', 1.5))
    
    ok, error = _send_with_retry(app, msg, recipient_info, retries=retries, delay_seconds=delay_seconds)
    if not ok:
        logger.error("❌ SMTP Error for %s: %s", recipient_info, error)

def send_eden_email(subject, recipient, body_html, background=False):
    """Primary helper for sending emails.

    Args:
        subject (str): email subject.
        recipient (str | list[str]): target address(es).
        body_html (str): HTML content.
        background (bool): if True, queue on thread and return immediately.
    """
    if not recipient or not body_html:
        logger.warning("⚠️ Invalid email data - missing recipient or body")
        return False, "Invalid email data"

    try:
        app_instance = current_app._get_current_object()
        sender_email = app_instance.config.get('MAIL_DEFAULT_SENDER') or app_instance.config.get('MAIL_USERNAME')
        sender_name = app_instance.config.get('MAIL_SENDER_NAME', 'The New Eden')

        if not sender_email or '@' not in str(sender_email):
            return False, "MAIL_DEFAULT_SENDER/MAIL_USERNAME is missing or invalid"
        
        recipients_list = [recipient] if isinstance(recipient, str) else recipient
        logger.info(f"📧 Queueing email to {recipients_list} with subject: {subject}")
        
        msg = Message(
            subject=subject,
            recipients=recipients_list,
            sender=formataddr((sender_name, str(sender_email))),
            html=body_html
        )

        # In serverless runtimes (e.g., Vercel), background threads can get pruned prematurely.
        if background and os.getenv('VERCEL'):
            logger.info("Serverless runtime detected; forcing synchronous email dispatch")
            background = False

        if background:
            # Precompile the message inside app context so the background thread
            # doesn't need the Flask application context later.
            try:
                with app_instance.app_context():
                    msg._compiled_string = msg.as_string()
            except Exception as e:
                logger.warning("Failed to pre-compile email for background send: %s", e)

            thread = threading.Thread(target=send_async_email, args=(app_instance, msg, recipients_list))
            thread.daemon = True
            thread.start()
            logger.info("📨 Email thread started")
            return True, "Email queued"

        # Synchronous send strategy
        retries = int(app_instance.config.get('MAIL_RETRY_COUNT', 2))
        delay_seconds = float(app_instance.config.get('MAIL_RETRY_DELAY', 1.5))
        ok, result = _send_with_retry(app_instance, msg, recipients_list, retries=retries, delay_seconds=delay_seconds)
        return ok, result

    except Exception as e:
        logger.error(f"❌ Email Dispatch Error: {str(e)}")
        return False, str(e)