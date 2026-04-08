import os
import re
import html
from flask import Blueprint, jsonify, request

from service.email_template import get_contact_admin_template, get_contact_ack_template
from service.send_email import send_eden_email

send_email_bp = Blueprint("send_email_bp", __name__)


def _is_valid_email(email: str) -> bool:
	return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email or ""))


@send_email_bp.route("/sendemail/message", methods=["POST"])
def send_contact_message():
	data = request.get_json(silent=True) or {}

	first_name = (data.get("firstName") or "").strip()
	last_name = (data.get("lastName") or "").strip()
	email = (data.get("email") or "").strip().lower()
	message = (data.get("message") or "").strip()

	first_name_safe = html.escape(first_name)
	last_name_safe = html.escape(last_name)
	email_safe = html.escape(email)
	message_safe = html.escape(message)

	if not first_name or not last_name or not email or not message:
		return jsonify({"ok": False, "message": "All fields are required"}), 400

	if not _is_valid_email(email):
		return jsonify({"ok": False, "message": "Invalid email address"}), 400

	if len(message) < 10:
		return jsonify({"ok": False, "message": "Message is too short"}), 400

	if len(message) > 5000:
		return jsonify({"ok": False, "message": "Message is too long"}), 400

	support_inbox = os.getenv("SUPPORT_INBOX", os.getenv("MAIL_DEFAULT_SENDER", "info@thenewedenagro.com"))

	body = get_contact_admin_template(first_name_safe, last_name_safe, email_safe, message_safe)

	subject = f"Contact Form: {first_name} {last_name}"
	success, error_message = send_eden_email(subject, support_inbox, body)

	if not success:
		return jsonify({"ok": False, "message": error_message or "Failed to queue email"}), 500

	# Send acknowledgement to user (non-blocking; does not fail the request)
	ack_subject = "We received your message • The New Eden"
	ack_body = get_contact_ack_template(first_name_safe)
	send_eden_email(ack_subject, email, ack_body, background=True)

	return jsonify({"ok": True, "message": "Message sent successfully"}), 200
