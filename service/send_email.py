import threading
import logging
import sys
from flask_mail import Message
from flask import current_app
from extensions import mail  # Import the neutral mail object

logger = logging.getLogger(__name__)

def send_async_email(app, msg, recipient_info):
    """Worker function for the background thread."""
    with app.app_context():
        try:
            sys.stdout.flush()
            mail.send(msg)
            success_msg = f"✅ Success: Email delivered to {recipient_info}"
            print(success_msg, flush=True)
            logger.info(success_msg)
            sys.stdout.flush()
        except Exception as e:
            error_msg = f"❌ SMTP Error for {recipient_info}: {str(e)}"
            print(error_msg, flush=True)
            logger.error(error_msg)
            sys.stdout.flush()

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
        print(msg, flush=True)
        return False, "Invalid email data"

    try:
        # Gets the real app object from the proxy
        app_instance = current_app._get_current_object()
        
        recipients_list = [recipient] if isinstance(recipient, str) else recipient
        queue_msg = f"📧 Queueing email to {recipients_list} with subject: {subject}"
        print(queue_msg, flush=True)
        logger.info(queue_msg)
        
        msg = Message(
            subject=subject,
            recipients=recipients_list,
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
            print(thread_msg, flush=True)
            logger.info(thread_msg)
            sys.stdout.flush()
            return True, "Email queued"

        # Synchronous send: return real SMTP success/failure to caller.
        mail.send(msg)
        success_msg = f"✅ Success: Email delivered to {recipients_list}"
        print(success_msg, flush=True)
        logger.info(success_msg)
        return True, "Email sent"
    except Exception as e:
        error_msg = str(e)
        exc_msg = f"❌ Email Dispatch Error: {error_msg}"
        print(exc_msg, flush=True)
        logger.error(exc_msg)
        return False, error_msg