"""Send one synthetic link-only callback email and check it (P0-08 test only).

Modes:
  (default)       send to local Mailpit (127.0.0.1:1025), read it back through Mailpit's API
                  (127.0.0.1:8025) and check it. Nothing leaves this computer.
  --smtp gmail    send one real email from a personal Gmail through smtp.gmail.com:587 (STARTTLS)
                  to a team mailbox. Environment (set in your own terminal, never committed):
                    SMTP_USER          the Gmail address you send from
                    SMTP_APP_PASSWORD  a Google app password (needs 2-Step Verification)
                    TEST_TO            a team mailbox (never a clinic or patient address)

All values are fake: random case ID, urgency, time. The output never shows addresses or passwords.
"""

import json
import os
import re
import smtplib
import ssl
import sys
import urllib.request
import uuid
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from zoneinfo import ZoneInfo

TEMPLATE = Path(__file__).resolve().parents[2] / "docs/integrations/admin-email/templates/link_only.txt"
CLINIC_TZ = ZoneInfo("America/New_York")  # synthetic clinic time zone
MAILPIT_SMTP = ("127.0.0.1", 1025)
MAILPIT_API = "http://127.0.0.1:8025/api/v1"
TIMEOUT = 20
SUBJECT_RE = re.compile(r"^\[ACTION NEEDED\] Patient callback request – (URGENT|Normal) – Case [0-9a-f-]{36}$")
FORBIDDEN = ("patient name", "date of birth", "dob", "phone:", "patnum", "whatsapp", "situation")


def render() -> tuple[str, str, str]:
    """Return (case_id, subject, body) rendered from the link_only template with fake values."""
    case_id = str(uuid.uuid4())
    values = {
        "urgency": "Normal",
        "received_at": datetime.now(CLINIC_TZ).strftime("%Y-%m-%d %H:%M %Z"),
        "case_id": case_id,
        "admin_console_base_url": "https://admin.example.invalid",
    }
    text = TEMPLATE.read_text(encoding="utf-8").format(**values)
    first, _, body = text.partition("\n")
    return case_id, first.removeprefix("Subject: "), body.lstrip("\n")


def content_problems(subject: str, body: str, case_id: str) -> list[str]:
    problems = []
    if not SUBJECT_RE.match(subject):
        problems.append("subject format")
    if "{" in subject + body:
        problems.append("unfilled placeholder")
    if f"/cases/{case_id}" not in body:
        problems.append("case link missing")
    lowered = body.lower()
    problems += [f"forbidden word '{w}'" for w in FORBIDDEN if w in lowered]
    return problems


def build(sender: str, to: str, subject: str, body: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = sender, to, subject
    msg.set_content(body)  # plain text only
    return msg


def report(checks: dict[str, bool]) -> int:
    for name, ok in checks.items():
        sys.stdout.write(f"{'PASS' if ok else 'FAIL'}  {name}\n")
    return 0 if all(checks.values()) else 1


def via_mailpit(case_id: str, subject: str, body: str) -> int:
    msg = build("callbacks@example.com", "frontdesk@example.com", subject, body)  # reserved example domain
    with smtplib.SMTP(*MAILPIT_SMTP, timeout=TIMEOUT) as smtp:
        smtp.send_message(msg)
    with urllib.request.urlopen(f"{MAILPIT_API}/search?query={case_id}", timeout=TIMEOUT) as r:  # noqa: S310 - local
        found = json.load(r).get("messages", [])
    if not found:
        return report({"message found in Mailpit": False})
    with urllib.request.urlopen(f"{MAILPIT_API}/message/{found[0]['ID']}", timeout=TIMEOUT) as r:  # noqa: S310
        stored = json.load(r)
    text = stored.get("Text", "")
    return report({
        "message found in Mailpit": True,
        "stored subject matches": stored.get("Subject") == subject,
        "stored body has the case link": f"/cases/{case_id}" in text,
        "stored body has no patient field": not content_problems(stored.get("Subject", ""), text, case_id),
        "plain text only (no HTML part)": not stored.get("HTML"),
    })


def via_gmail(subject: str, body: str) -> int:
    user = os.environ.get("SMTP_USER", "").strip()
    password = "".join(os.environ.get("SMTP_APP_PASSWORD", "").split())  # app passwords are shown with spaces
    to = os.environ.get("TEST_TO", "").strip()
    if not (user and password and to):
        sys.stderr.write("Set SMTP_USER, SMTP_APP_PASSWORD and TEST_TO first.\n")
        return 2
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=TIMEOUT) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        tls = smtp.sock.version() if hasattr(smtp.sock, "version") else "unknown"
        try:
            smtp.login(user, password)
        except smtplib.SMTPAuthenticationError as err:
            sys.stderr.write(f"Login refused (SMTP {err.smtp_code}). Check the app password and 2-Step Verification.\n")
            return 1
        smtp.send_message(build(user, to, subject, body))
    sys.stdout.write(f"Sent over {tls} to the team mailbox.\n")
    sys.stdout.write("Now open it, choose 'Show original', and look for 'TLS' in Received and 'dkim=pass'.\n")
    return 0


def main() -> int:
    if sys.argv[1:] not in ([], ["--smtp", "gmail"]):
        sys.stderr.write("Usage: send_test_callback_email.py [--smtp gmail]\n")
        return 2
    case_id, subject, body = render()
    problems = content_problems(subject, body, case_id)
    if problems:
        sys.stderr.write("Rendered email failed checks: " + ", ".join(problems) + "\n")
        return 1
    sys.stdout.write(f"Rendered link-only email for synthetic case {case_id}\n")
    try:
        return via_gmail(subject, body) if sys.argv[1:] else via_mailpit(case_id, subject, body)
    except (OSError, smtplib.SMTPException) as err:
        sys.stderr.write(f"Could not send: {type(err).__name__}. Is the SMTP server reachable?\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
