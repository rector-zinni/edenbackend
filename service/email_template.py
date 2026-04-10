import os


def _resolve_logo_src():
    """Return logo URL from environment for independently hosted backend."""
    env_logo = os.getenv("NEW_EDEN_LOGO_URL", "").strip()
    if env_logo:
        return env_logo

    return ""


def get_email_wrapper(content_html, preheader="Fresh updates from The New Eden"):
    """Wrap all emails with a modern, responsive-friendly Eden layout."""
    logo_url = _resolve_logo_src()
    logo_block = (
        f"<img src=\"{logo_url}\" alt=\"The New Eden\" width=\"56\" height=\"56\" style=\"display:block; width:56px; height:56px; border-radius:14px; margin-bottom:10px;\" />"
        if logo_url
        else ""
    )

    return f"""
        <!doctype html>
        <html>
            <head>
                <meta charset="utf-8" />
                <meta name="viewport" content="width=device-width, initial-scale=1" />
                <title>The New Eden</title>
            </head>
            <body style="margin:0; padding:0; background:#f4f8f4; font-family: Inter, Segoe UI, Arial, sans-serif; color:#122015;">
                <div style="display:none; max-height:0; overflow:hidden; opacity:0;">
                    {preheader}
                </div>

                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f4f8f4; padding:24px 10px;">
                    <tr>
                        <td align="center">
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:640px; background:#ffffff; border:1px solid #dce9dc; border-radius:18px; overflow:hidden; box-shadow:0 10px 25px rgba(17, 24, 39, 0.08);">
                                <tr>
                                    <td style="background:linear-gradient(135deg, #154212 0%, #2d5a27 100%); padding:28px 28px 22px 28px;">
                                        {logo_block}
                                        <p style="margin:0; font-size:12px; letter-spacing:1.2px; text-transform:uppercase; color:#b8e6c4; font-weight:700;">The New Eden</p>
                                        <h1 style="margin:8px 0 0 0; color:#ffffff; font-size:26px; line-height:1.2;">Farm-fresh updates for you</h1>
                                    </td>
                                </tr>

                                <tr>
                                    <td style="padding:28px;">
                                        {content_html}
                                    </td>
                                </tr>

                                <tr>
                                    <td style="padding:16px 28px 28px 28px;">
                                        <div style="border-top:1px solid #e5efe5; padding-top:16px;">
                                            <p style="margin:0; color:#48614b; font-size:12px; line-height:1.6;">
                                                © 2026 The New Eden · Southwestern Nigeria<br/>
                                                Connecting local farmers to your doorstep.
                                            </p>
                                        </div>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </body>
        </html>
        """

def get_order_template(user_name, order_id, amount, items):
    items_list = "".join([f"<li>{i['name']} (x{i['quantity']})</li>" for i in items])
    content = f"""
        <h2 style="color:#122015; margin:0 0 10px 0;">Order Confirmed ✅</h2>
        <p style="margin:0 0 14px 0; color:#2f4333;">Hi {user_name}, we've received your order <strong>#{order_id[-6:].upper()}</strong>.</p>
        <div style="background:#f7fbf7; border-radius:12px; padding:18px; margin:18px 0; border:1px solid #e3eee3;">
            <ul style="padding-left:20px; margin:0; color:#1f3123;">{items_list}</ul>
            <p style="margin-top:15px; border-top:1px solid #dce9dc; padding-top:10px; font-weight:700; color:#154212;">
                Total Amount: ₦{amount:,.2f}
            </p>
        </div>
        <p style="margin:0; color:#2f4333;">Our team in Lagos is preparing your delivery. You'll get another update once it's on the way.</p>
    """
    return get_email_wrapper(content, preheader="Your New Eden order has been confirmed")

def get_welcome_template(user_name):
    content = f"""
        <h2 style="color:#122015; margin:0 0 10px 0;">Welcome to the Garden, {user_name} 🌱</h2>
        <p style="margin:0 0 14px 0; color:#2f4333;">Your account with <strong>The New Eden</strong> is now active. You can now browse fresh produce directly from local Southwestern Nigerian farms.</p>
        <div style="text-align:center; margin:24px 0;">
            <a href="#" style="display:inline-block; background:#15803d; color:white; padding:12px 24px; text-decoration:none; border-radius:10px; font-weight:700;">Start Shopping</a>
        </div>
        <p style="margin:0; color:#2f4333;">If you have any questions about our sourcing or delivery, just reply to this email.</p>
    """
    return get_email_wrapper(content, preheader="Welcome to The New Eden")

def get_password_reset_template(reset_link):
    content = f"""
        <h2 style="color:#122015; margin:0 0 10px 0;">Reset Your Password</h2>
        <p style="margin:0 0 14px 0; color:#2f4333;">We received a request to reset your password for The New Eden. Click the button below to choose a new one:</p>
        <div style="text-align:center; margin:24px 0;">
            <a href="{reset_link}" style="display:inline-block; background:#1e293b; color:white; padding:12px 24px; text-decoration:none; border-radius:10px; font-weight:700;">Reset Password</a>
        </div>
        <p style="margin:0; font-size:13px; color:#6b7f6f;">If you didn't request this, you can safely ignore this email. This link will expire in 1 hour.</p>
    """
    return get_email_wrapper(content, preheader="Password reset request")


def get_admin_new_order_template(order_id, user_email, total_amount, items, shipping_address=None):
    items_list = "".join([
        f"<li style='margin-bottom:4px;'>{i.get('name','Item')} &times; {i.get('quantity',1)} — ₦{float(i.get('price',0)):,.2f}</li>"
        for i in (items or [])
    ])
    address_block = ""
    if shipping_address:
        address_block = f"<p style='margin:10px 0 0 0; color:#2f4333;'><strong>Delivery to:</strong> {shipping_address}</p>"
    content = f"""
        <h2 style="color:#122015; margin:0 0 10px 0;">🛒 New Order Received</h2>
        <p style="margin:0 0 6px 0; color:#2f4333;"><strong>Order ID:</strong> #{order_id[-6:].upper()}</p>
        <p style="margin:0 0 14px 0; color:#2f4333;"><strong>Customer:</strong> {user_email}</p>
        <div style="background:#f7fbf7; border-radius:12px; padding:18px; margin:14px 0; border:1px solid #e3eee3;">
            <ul style="padding-left:20px; margin:0; color:#1f3123;">{items_list}</ul>
            <p style="margin-top:14px; border-top:1px solid #dce9dc; padding-top:10px; font-weight:700; color:#154212;">
                Total: ₦{float(total_amount):,.2f}
            </p>
        </div>
        {address_block}
        <p style="margin:12px 0 0 0; color:#48614b; font-size:13px;">Payment status: <strong>Awaiting Payment</strong></p>
    """
    return get_email_wrapper(content, preheader=f"New order #{order_id[-6:].upper()} from {user_email}")


def get_admin_payment_confirmed_template(order_id, user_email, total_amount, items, payment_reference=None):
    items_list = "".join([
        f"<li style='margin-bottom:4px;'>{i.get('name','Item')} &times; {i.get('quantity',1)} — ₦{float(i.get('price',0)):,.2f}</li>"
        for i in (items or [])
    ])
    ref_block = f"<p style='margin:8px 0 0 0; color:#48614b; font-size:13px;'><strong>Reference:</strong> {payment_reference}</p>" if payment_reference else ""
    content = f"""
        <h2 style="color:#122015; margin:0 0 10px 0;">💰 Payment Confirmed — Order Ready to Process</h2>
        <p style="margin:0 0 6px 0; color:#2f4333;"><strong>Order ID:</strong> #{order_id[-6:].upper()}</p>
        <p style="margin:0 0 14px 0; color:#2f4333;"><strong>Customer:</strong> {user_email}</p>
        <div style="background:#f7fbf7; border-radius:12px; padding:18px; margin:14px 0; border:1px solid #e3eee3;">
            <ul style="padding-left:20px; margin:0; color:#1f3123;">{items_list}</ul>
            <p style="margin-top:14px; border-top:1px solid #dce9dc; padding-top:10px; font-weight:700; color:#154212;">
                Amount Paid: ₦{float(total_amount):,.2f}
            </p>
        </div>
        {ref_block}
        <p style="margin:12px 0 0 0; color:#48614b; font-size:13px;">Status updated to <strong>Processing</strong>. Please prepare for dispatch.</p>
    """
    return get_email_wrapper(content, preheader=f"Payment confirmed for order #{order_id[-6:].upper()}")


def get_contact_admin_template(first_name, last_name, email, message):
    content = f"""
        <h2 style="color:#122015; margin:0 0 10px 0;">New Contact Form Message</h2>
        <p style="margin:0 0 10px 0; color:#2f4333;"><strong>From:</strong> {first_name} {last_name}</p>
        <p style="margin:0 0 16px 0; color:#2f4333;"><strong>Email:</strong> {email}</p>
        <div style="background:#f7fbf7; border:1px solid #e3eee3; border-radius:12px; padding:16px;">
            <p style="margin:0; color:#1f3123; white-space:pre-wrap;">{message}</p>
        </div>
    """
    return get_email_wrapper(content, preheader=f"New message from {first_name} {last_name}")


def get_contact_ack_template(first_name):
    content = f"""
        <h2 style="color:#122015; margin:0 0 10px 0;">We got your message, {first_name} 👋</h2>
        <p style="margin:0 0 12px 0; color:#2f4333;">Thanks for reaching out to The New Eden support team.</p>
        <p style="margin:0 0 16px 0; color:#2f4333;">We usually respond within <strong>5 minutes</strong> during active support hours.</p>
        <div style="background:#f7fbf7; border:1px solid #e3eee3; border-radius:12px; padding:16px; color:#1f3123;">
            If your request is urgent (delivery or payment issue), please reply to this email with your order ID.
        </div>
    """
    return get_email_wrapper(content, preheader="We received your support request")