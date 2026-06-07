from config.env_loader import load_env_file
import os
import smtplib
import ssl
import traceback

# Load .env same as app
load_env_file()

HOST = os.getenv('MAIL_SERVER')
PORT = int(os.getenv('MAIL_PORT', '587'))
USE_SSL = os.getenv('MAIL_USE_SSL', 'false').strip().lower() in ('1','true','yes')
USE_TLS = os.getenv('MAIL_USE_TLS', 'false').strip().lower() in ('1','true','yes')
USER = os.getenv('MAIL_USERNAME')
PWD = os.getenv('MAIL_PASSWORD')
TIMEOUT = int(os.getenv('MAIL_TIMEOUT', '20'))

print('SMTP TEST')
print('HOST', HOST)
print('PORT', PORT)
print('USE_SSL', USE_SSL)
print('USE_TLS', USE_TLS)
print('USER', USER)
print('TIMEOUT', TIMEOUT)

ctx = ssl.create_default_context()

# Try connecting according to configuration
try:
    if USE_SSL or PORT == 465:
        print('Attempting SMTP_SSL...')
        with smtplib.SMTP_SSL(HOST, PORT, context=ctx, timeout=TIMEOUT) as s:
            s.ehlo()
            if USER and PWD:
                s.login(USER, PWD)
            print('SMTP_SSL connected and login successful')
    else:
        print('Attempting SMTP (plain) then STARTTLS if configured...')
        with smtplib.SMTP(HOST, PORT, timeout=TIMEOUT) as s:
            s.ehlo()
            if USE_TLS:
                print('Starting STARTTLS...')
                s.starttls(context=ctx)
                s.ehlo()
            if USER and PWD:
                s.login(USER, PWD)
            print('SMTP connected and login successful')
except Exception as e:
    print('SMTP test failed:')
    traceback.print_exc()

# Also test explicit 465 and 587 attempts for diagnostics
print('\n--- Additional checks ---')
for test_port, test_method in ((465,'SSL'), (587,'STARTTLS')):
    try:
        print(f'\nTesting {test_method} on port {test_port}...')
        if test_method == 'SSL':
            with smtplib.SMTP_SSL(HOST, test_port, context=ctx, timeout=TIMEOUT) as s:
                s.ehlo()
                print('Banner:', s.sock.getpeername())
        else:
            with smtplib.SMTP(HOST, test_port, timeout=TIMEOUT) as s:
                s.ehlo()
                code = s.noop()[0]
                print('NOOP code:', code)
    except Exception:
        traceback.print_exc()
