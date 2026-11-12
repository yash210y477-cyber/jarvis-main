"""Telegram user-account session for real voice calls.

Bots cannot place or receive Telegram calls, so JARVIS needs its own user
account. The phone number is used once during the OTP login; afterwards the
saved session string is enough.
"""

from pathlib import Path

from config.settings import settings


DEFAULT_SESSION = (
    Path(__file__).resolve().parents[1] / "data" / "telegram_user.session"
)

_PENDING = {}


class TelegramUserSession:
    """API credentials plus the saved user session."""

    def __init__(self, api_id=None, api_hash="", session_path=None):

        self.api_id = int(api_id or settings.TELEGRAM_API_ID or 0)

        self.api_hash = api_hash or settings.TELEGRAM_API_HASH or ""

        self.session_path = Path(session_path or DEFAULT_SESSION)

    def configured(self) -> bool:

        return bool(self.api_id and self.api_hash)

    def session_string(self) -> str:

        try:

            return self.session_path.read_text(encoding="utf-8").strip()

        except OSError:

            return ""

    def save_session(self, value: str) -> None:

        self.session_path.parent.mkdir(parents=True, exist_ok=True)

        self.session_path.write_text((value or "").strip(), encoding="utf-8")

    def clear_session(self) -> None:

        try:

            self.session_path.unlink()

        except OSError:

            pass

    def build(self):
        """Telethon client using the saved session (not connected yet)."""

        from telethon import TelegramClient
        from telethon.sessions import StringSession

        if not self.configured():

            raise RuntimeError(
                "TELEGRAM_API_ID and TELEGRAM_API_HASH are required."
            )

        return TelegramClient(
            StringSession(self.session_string() or None),
            self.api_id,
            self.api_hash,
        )

    def status(self) -> dict:

        return {
            "configured": self.configured(),
            "session": bool(self.session_string()),
            "enabled": self.configured() and bool(self.session_string()),
            "needs_api_id": not self.configured(),
        }


async def start_login(phone: str, session: TelegramUserSession = None) -> dict:

    session = session or TelegramUserSession()

    phone = (phone or "").strip()

    if not phone:

        return {"success": False, "error": "A phone number is required."}

    if not session.configured():

        return {
            "success": False,
            "error": (
                "Set TELEGRAM_API_ID and TELEGRAM_API_HASH first "
                "(https://my.telegram.org)."
            ),
        }

    previous = _PENDING.get("client")

    if previous is not None:

        try:

            await previous.disconnect()

        except Exception:

            pass

    try:

        from telethon import TelegramClient
        from telethon.sessions import StringSession

        client = TelegramClient(
            StringSession(), session.api_id, session.api_hash
        )

        await client.connect()

        sent = await client.send_code_request(phone)

    except Exception as error:

        _PENDING.clear()

        return {"success": False, "error": str(error)}

    _PENDING.clear()
    _PENDING.update(
        {
            "client": client,
            "phone": phone,
            "hash": getattr(sent, "phone_code_hash", None),
            "session": session,
        }
    )

    return {
        "success": True,
        "phone": phone,
        "message": "Telegram sent a login code. Send it back to finish.",
    }


async def verify_login(
    code: str, password: str = "", session: TelegramUserSession = None
) -> dict:

    pending = _PENDING.get("client")

    if pending is None:

        return {
            "success": False,
            "error": "Start the login first with /telegram-call/login/start.",
        }

    session = session or _PENDING.get("session") or TelegramUserSession()

    phone = _PENDING.get("phone")

    code_hash = _PENDING.get("hash")

    try:

        from telethon.errors import SessionPasswordNeededError

    except Exception:

        SessionPasswordNeededError = Exception

    try:

        await pending.sign_in(
            phone=phone, code=(code or "").strip(), phone_code_hash=code_hash
        )

    except SessionPasswordNeededError:

        if not password:

            return {
                "success": False,
                "needs_password": True,
                "error": "This account has two-step verification; send the password.",
            }

        try:

            await pending.sign_in(password=password)

        except Exception as error:

            return {"success": False, "error": str(error)}

    except Exception as error:

        return {"success": False, "error": str(error)}

    if not await pending.is_user_authorized():

        return {"success": False, "error": "Telegram did not authorise the session."}

    me = await pending.get_me()

    session.save_session(pending.session.save())

    try:

        await pending.disconnect()

    except Exception:

        pass

    _PENDING.clear()

    return {
        "success": True,
        "user": {
            "id": getattr(me, "id", None),
            "name": " ".join(
                part
                for part in (
                    getattr(me, "first_name", "") or "",
                    getattr(me, "last_name", "") or "",
                )
                if part
            ).strip(),
            "username": getattr(me, "username", None),
        },
        "message": "Logged in. JARVIS can now receive calls on this account.",
    }
