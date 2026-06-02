"""Send a test email using the same SMTP settings as the Flask app.

Usage (from project root):
    python scripts/test_mail.py you@example.com
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flask_app import create_app
from flask_mail import Message

from flask_app.extensions import mail


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_mail.py recipient@example.com")
        return 1

    recipient = sys.argv[1].strip()
    app = create_app()

    with app.app_context():
        if app.config.get("MAIL_SUPPRESS_SEND"):
            print("Mail is NOT configured (missing MAIL_USERNAME or MAIL_PASSWORD).")
            print("Edit flask_app/.env and restart.")
            return 1

        print(
            f"Sending test via {app.config['MAIL_SERVER']}:{app.config['MAIL_PORT']} "
            f"as {app.config['MAIL_USERNAME']} -> {recipient}"
        )
        msg = Message(
            subject="UrbanCart mail test",
            recipients=[recipient],
            body="If you received this, SMTP is working.",
            sender=app.config["MAIL_DEFAULT_SENDER"],
        )
        try:
            mail.send(msg)
        except Exception as exc:
            print("FAILED:", exc)
            return 1

        print("OK — check inbox and spam.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
