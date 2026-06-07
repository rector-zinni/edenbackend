from app import app
from service.send_email import send_eden_email
import time

with app.app_context():
    ok, msg = send_eden_email('BG Test — Unicode —', 'testrecipient@example.com', '<p>Testing em dash — and unicode ✓</p>', background=True)
    print('queued:', ok, msg)

# wait for background thread to finish
print('waiting for thread...')
time.sleep(5)
print('done')
