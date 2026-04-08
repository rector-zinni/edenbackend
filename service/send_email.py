import threading
import logging
import time
import socket
import smtplib
from email.utils import formataddr
from flask_mail import Message
from flask import current_app
from extensions import mail  # Import the neutral mail object

logger = logging.getLogger(__name__)


def _send_with_retry(msg, recipient_info, retries=2, delay_seconds=1.5):
    last_error = None

    for attempt in range(1, retries + 2):
        try:
            mail.send(msg)
            success_msg = f"✅ Success: Email delivered to {recipient_info}"
            logger.info(success_msg)
            return True, "Email sent"
        except (ConnectionResetError, BrokenPipeError, socket.timeout, TimeoutError,
                smtplib.SMTPServerDisconnected, OSError) as exc:
            last_error = exc
            if attempt <= retries:
                logger.warning(
                    "SMTP transient error for %s (attempt %s/%s): %s",
                    recipient_info,
                    attempt,
                    retries + 1,
                    str(exc),
                )
                time.sleep(delay_seconds)
                continue
            break
        except Exception as exc:
            last_error = exc
            break

    return False, str(last_error) if last_error else "Unknown SMTP error"

def send_async_email(app, msg, recipient_info):
    """Worker function for the background thread."""
    with app.app_context():
        retries = int(app.config.get('MAIL_RETRY_COUNT', 2))
        delay_seconds = float(app.config.get('MAIL_RETRY_DELAY', 1.5))
        ok, error = _send_with_retry(msg, recipient_info, retries=retries, delay_seconds=delay_seconds)
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
        msg = f"⚠️  Invalid email data - recipient: {recipient}, body: {'<present>' if body_html else '<missing>'}"
        logger.warning(msg)
        return False, "Invalid email data"

    try:
        # Gets the real app object from the proxy
        app_instance = current_app._get_current_object()
        sender_email = app_instance.config.get('MAIL_DEFAULT_SENDER') or app_instance.config.get('MAIL_USERNAME')
        sender_name = app_instance.config.get('MAIL_SENDER_NAME', 'The New Eden')

        if not sender_email or '@' not in str(sender_email):
            return False, "MAIL_DEFAULT_SENDER/MAIL_USERNAME is missing or invalid"
        
        recipients_list = [recipient] if isinstance(recipient, str) else recipient
        queue_msg = f"📧 Queueing email to {recipients_list} with subject: {subject}"
        logger.info(queue_msg)
        
        msg = Message(
            subject=subject,
            recipients=recipients_list,
            sender=formataddr((sender_name, str(sender_email))),
            html=body_html
        )

        if background:
            # Fire and forget.
            def send_wrapper():
                send_async_email(app_instance, msg, recipients_list)

            thread = threading.Thread(target=send_wrapper)
            thread.daemon = True
            thread.start()

            thread_msg = "📨 Email thread started"
            logger.info(thread_msg)
            return True, "Email queued"

        # Synchronous send: return real SMTP success/failure to caller.
        retries = int(app_instance.config.get('MAIL_RETRY_COUNT', 2))
        delay_seconds = float(app_instance.config.get('MAIL_RETRY_DELAY', 1.5))
        ok, result = _send_with_retry(msg, recipients_list, retries=retries, delay_seconds=delay_seconds)
        if ok:
            return True, result
        return False, result
    except Exception as e:
        error_msg = str(e)
        exc_msg = f"❌ Email Dispatch Error: {error_msg}"
        logger.error(exc_msg)
        return False, error_msg