"""Email on the user's own mailbox: SMTP to send, IMAP to read.

No provider SDK and no extra dependency: both protocols ship with Python, so the
only setup is the mailbox address and an app password in backend/.env.

    SMTP_HOST=smtp.gmail.com   SMTP_PORT=465   SMTP_USER=you@gmail.com
    SMTP_PASSWORD=<app password>              SMTP_FROM=you@gmail.com
    IMAP_HOST=imap.gmail.com   IMAP_PORT=993

Sending is a "confirm" tool: the chat asks first and a refused approval sends
nothing. Reading is confirm-gated too, because an inbox is private.
"""

import email
import imaplib
import smtplib
import ssl
from email.header import decode_header, make_header
from email.message import EmailMessage

from config.settings import settings

SETUP_HINT = (
    "Email is not set up yet. Put SMTP_HOST, SMTP_USER and SMTP_PASSWORD in "
    "backend/.env (Gmail needs an app password), then restart the backend."
)

READ_HINT = (
    "Inbox reading is not set up yet. Put IMAP_HOST, SMTP_USER and "
    "SMTP_PASSWORD in backend/.env, then restart the backend."
)


def _smtp() -> tuple[str, int, str, str, str]:
    host = (getattr(settings, "SMTP_HOST", "") or "").strip()
    port = int(getattr(settings, "SMTP_PORT", 465) or 465)
    user = (getattr(settings, "SMTP_USER", "") or "").strip()
    password = getattr(settings, "SMTP_PASSWORD", "") or ""
    sender = (getattr(settings, "SMTP_FROM", "") or "").strip() or user

    return host, port, user, password, sender


def _imap() -> tuple[str, int, str, str]:
    host = (getattr(settings, "IMAP_HOST", "") or "").strip()
    port = int(getattr(settings, "IMAP_PORT", 993) or 993)
    user = (getattr(settings, "SMTP_USER", "") or "").strip()
    password = getattr(settings, "SMTP_PASSWORD", "") or ""

    return host, port, user, password


def _header(value) -> str:
    """Decode =?utf-8?...?= headers into readable text."""

    if not value:
        return ""

    try:

        return str(make_header(decode_header(str(value)))).strip()

    except Exception:

        return str(value).strip()


def send_email(to: str, subject: str, body: str, cc: str = "") -> dict:
    """Send one plain-text email. The chat asks for approval before this runs."""

    recipient = (to or "").strip()
    subject = (subject or "").strip()
    body = (body or "").strip()
    cc = (cc or "").strip()

    if not recipient or "@" not in recipient:

        return {"success": False, "error": "Which email address should I send to?"}

    if not subject and not body:

        return {"success": False, "error": "What should the email say?"}

    host, port, user, password, sender = _smtp()

    if not (host and user and password):

        return {"success": False, "error": SETUP_HINT, "setup": True}

    message = EmailMessage()

    message["From"] = sender
    message["To"] = recipient

    if cc:

        message["Cc"] = cc

    message["Subject"] = subject or "(no subject)"
    message.set_content(body or "")

    recipients = [recipient] + ([cc] if cc else [])

    try:

        if getattr(settings, "SMTP_SSL", True):

            with smtplib.SMTP_SSL(
                host, port, timeout=25, context=ssl.create_default_context()
            ) as server:

                server.login(user, password)
                server.send_message(message, to_addrs=recipients)

        else:

            with smtplib.SMTP(host, port, timeout=25) as server:

                server.starttls(context=ssl.create_default_context())
                server.login(user, password)
                server.send_message(message, to_addrs=recipients)

    except Exception as error:

        return {"success": False, "error": f"Could not send the email: {error}"}

    return {
        "success": True,
        "to": recipient,
        "cc": cc,
        "subject": subject,
        "message": f"Email sent to {recipient}.",
    }


def read_inbox(limit: int = 5, unread_only: bool = False) -> dict:
    """The newest messages in the inbox: sender, subject and date."""

    host, port, user, password = _imap()

    if not (host and user and password):

        return {"success": False, "error": READ_HINT, "setup": True}

    try:

        limit = max(1, min(25, int(limit or 5)))

    except (TypeError, ValueError):

        limit = 5

    try:

        with imaplib.IMAP4_SSL(host, port, timeout=25) as box:

            box.login(user, password)
            box.select("INBOX", readonly=True)

            typ, data = box.search(None, "(UNSEEN)" if unread_only else "ALL")

            ids = (data[0].split() if data and data[0] else [])[-limit:]

            messages = []

            for message_id in reversed(ids):

                typ, raw = box.fetch(message_id, "(RFC822)")

                if typ != "OK" or not raw or not isinstance(raw[0], tuple):

                    continue

                parsed = email.message_from_bytes(raw[0][1])

                messages.append(
                    {
                        "from": _header(parsed.get("From")),
                        "subject": _header(parsed.get("Subject")),
                        "date": _header(parsed.get("Date")),
                    }
                )

    except Exception as error:

        return {"success": False, "error": f"Could not read the inbox: {error}"}

    return {
        "success": True,
        "count": len(messages),
        "unread_only": bool(unread_only),
        "messages": messages,
        "message": (
            f"{len(messages)} message(s) in the inbox."
            if messages
            else "The inbox has nothing to show."
        ),
    }
