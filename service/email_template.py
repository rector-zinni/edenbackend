def get_email_wrapper(content_html):
    """Wraps all emails in a consistent Eden branding."""
    return f"""
    <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #1e293b; background-color: #f8fafc; padding: 40px 10px;">
        <div style="max-width: 600px; margin: auto; background: #ffffff; border-radius: 12px; overflow: hidden; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);">
            <div style="background-color: #15803d; padding: 30px; text-align: center;">
                <h1 style="color: white; margin: 0; font-size: 28px; letter-spacing: -0.025em;">The New Eden</h1>
                <p style="color: #d1fae5; margin: 5px 0 0 0; font-size: 14px;">Pure. Fresh. Local.</p>
            </div>
            <div style="padding: 40px 30px;">
                {content_html}
            </div>
            <div style="background-color: #f1f5f9; padding: 20px; text-align: center; font-size: 12px; color: #64748b;">
                <p style="margin: 0;">© 2026 The New Eden | Southwestern Nigeria</p>
                <p style="margin: 5px 0 0 0;">Connecting local farmers to your doorstep.</p>
            </div>
        </div>
    </div>
    """

def get_order_template(user_name, order_id, amount, items):
    items_list = "".join([f"<li>{i['name']} (x{i['quantity']})</li>" for i in items])
    content = f"""
        <h2 style="color: #0f172a;">Order Confirmed!</h2>
        <p>Hi {user_name}, we've received your order <strong>#{order_id[-6:].upper()}</strong>.</p>
        <div style="background: #f8fafc; border-radius: 8px; padding: 20px; margin: 20px 0;">
            <ul style="padding-left: 20px; margin: 0;">{items_list}</ul>
            <p style="margin-top: 15px; border-top: 1px solid #e2e8f0; pt: 10px; font-weight: bold;">
                Total Amount: ₦{amount:,.2f}
            </p>
        </div>
        <p>Our team in Lagos is preparing your delivery. You'll get another update once it's on the way!</p>
    """
    return get_email_wrapper(content)

def get_welcome_template(user_name):
    content = f"""
        <h2 style="color: #0f172a;">Welcome to the Garden, {user_name}!</h2>
        <p>Your account with <strong>The New Eden</strong> is now active. You can now browse fresh produce directly from local Southwestern Nigerian farms.</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="#" style="background: #15803d; color: white; padding: 12px 25px; text-decoration: none; border-radius: 6px; font-weight: bold;">Start Shopping</a>
        </div>
        <p>If you have any questions about our sourcing or delivery, just reply to this email!</p>
    """
    return get_email_wrapper(content)

def get_password_reset_template(reset_link):
    content = f"""
        <h2 style="color: #0f172a;">Reset Your Password</h2>
        <p>We received a request to reset your password for The New Eden. Click the button below to choose a new one:</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{reset_link}" style="background: #1e293b; color: white; padding: 12px 25px; text-decoration: none; border-radius: 6px; font-weight: bold;">Reset Password</a>
        </div>
        <p style="font-size: 13px; color: #94a3b8;">If you didn't request this, you can safely ignore this email. This link will expire in 1 hour.</p>
    """
    return get_email_wrapper(content)