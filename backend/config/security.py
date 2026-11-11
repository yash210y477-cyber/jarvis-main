"""
Local-only request guard.

JARVIS exposes privileged endpoints (launch an app, start the microphone) on
loopback. Browsers will happily send "simple" cross-site POSTs, so CORS alone
does not stop a random website from triggering those side effects. Every
state-changing request must therefore come from an allowed local origin.
"""

from typing import Optional

from config.settings import settings

STATE_CHANGING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def normalize_origin(origin: Optional[str]) -> str:
    """Lower-case an origin and strip any trailing slash."""

    if not origin:
        return ""

    return origin.strip().lower().rstrip("/")


def is_allowed_origin(origin: Optional[str]) -> bool:
    """
    Return True when a request origin is acceptable.

    - Missing Origin: native clients (curl, python, the voice thread) and
      same-origin navigations.
    """

    normalized = normalize_origin(origin)

    if not normalized:
        return True

    allowed = {normalize_origin(item) for item in settings.ALLOWED_ORIGINS}

    return normalized in allowed


def check_request(method: str, headers) -> Optional[str]:
    """
    Validate a state-changing HTTP request.

    Returns an error string when the request must be rejected, otherwise None.
    """

    if method.upper() not in STATE_CHANGING_METHODS:
        return None

    origin = headers.get("origin")

    if not is_allowed_origin(origin):
        return "Origin not allowed."

    # Modern browsers send this. "same-site" is normal for the local UI
    # (localhost:5173 -> localhost:8000), so only true cross-site is blocked.
    if (headers.get("sec-fetch-site") or "").lower() == "cross-site":
        return "Cross-site request rejected."

    token = settings.LOCAL_TOKEN

    if token and headers.get("x-jarvis-token") != token:
        return "Missing or invalid local token."

    return None
