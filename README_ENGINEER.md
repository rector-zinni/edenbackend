# Eden Backend Engineering Docs

## Project Purpose
Eden backend is a Flask API for The New Eden platform, integrating with Firebase and email/push notifications.

## Stack
- Python 3
- Flask
- Firebase Admin SDK (`firebase_admin`) for Firestore
- Flask-Mail for SMTP
- Exponent Server SDK for Expo push notifications

## Key modules
- `app.py` — app initialization, CORS, Mail config, routes registration.
- `route/` folder — blueprints for each domain:
  - `createuser.py` (user sync, guest signup)
  - `order.py` (orders, update status)
  - `payment.py`, `deliveryfee.py`, etc.
- `service/` — utilities:
  - `send_email.py` send_eden_email (async thread)
  - `notification.py` send_push_notification
  - `email_template.py` email templates

## Order status email behavior
- `route/order.py` `update_order_status` updates Firestore and:
  - sends push notification by `userId` type (guest/user)
  - reads `user_email` from order document as fallback for guest orders
  - if user document exists, uses `user_data.email` and name

## Running server
1. `cd edenbackend`
2. `pip install -r requirements.txt`
3. `python app.py`
4. Endpoint: `http://localhost:5000`.

## Important notes
- Make sure `MAIL_*` config uses valid SMTP cred.
- `is_guest` guest orders store customer email in order document.
- `test-email` route for SMTP health check.

## Troubleshooting
- `curl -X POST http://localhost:5000/api/test-email -H 'Content-Type: application/json' -d '{"email":"your@mail.com"}'`
- Check logs in `server.log` or console.

## TODO
- Add request logging and structured error responses.
- Add token auth to admin endpoints.
- Add transactional writes for order+notifications.
