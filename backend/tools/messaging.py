"""Send a message on whichever chat app the user names.

Two strategies, because chat apps differ:

* ``search`` — apps with a keyboard search (WhatsApp, Telegram Desktop): bring
  the app forward, Ctrl+F, type the contact, open the first hit, paste the text.
* ``web`` — everything else (Instagram, Messenger, Discord, Slack, LinkedIn,
  X, Reddit): open the site and let the screen agent click its way to the chat.

Nothing is sent unless ``confirm`` is true. Without it the text is left in the
compose box so the user can read it before pressing send.
"""

import ctypes
import json
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

BACKEND = Path(__file__).resolve().parents[1]
CONTACTS = BACKEND / "data" / "contacts.json"

PLATFORMS = {
    "whatsapp": {
        "strategy": "search",
        "app": "whatsapp",
        "window": ("WhatsApp",),
        "web": "https://web.whatsapp.com",
        "link": "https://wa.me/{phone}?text={text}",
    },
    "telegram": {
        "strategy": "search",
        "app": "telegram",
        "window": ("Telegram",),
        "web": "https://web.telegram.org",
        "link": "tg://resolve?domain={username}&text={text}",
    },
    "instagram": {
        "strategy": "web",
        "web": "https://www.instagram.com/direct/new/",
        "inbox": "https://www.instagram.com/direct/inbox/",
    },
    "messenger": {"strategy": "web", "web": "https://www.messenger.com"},
    "facebook": {"strategy": "web", "web": "https://www.facebook.com/messages"},
    "discord": {"strategy": "web", "web": "https://discord.com/app"},
    "slack": {"strategy": "web", "web": "https://app.slack.com/client"},
    "linkedin": {"strategy": "web", "web": "https://www.linkedin.com/messaging"},
    "x": {"strategy": "web", "web": "https://x.com/messages"},
    "twitter": {"strategy": "web", "web": "https://x.com/messages"},
    "reddit": {"strategy": "web", "web": "https://chat.reddit.com"},
    "sms": {"strategy": "link", "link": "sms:?body={text}"},
    "email": {"strategy": "link", "link": "mailto:{email}?body={text}"},
}

ALIASES = {
    "wa": "whatsapp",
    "whatsapp desktop": "whatsapp",
    "tg": "telegram",
    "telegram desktop": "telegram",
    "insta": "instagram",
    "ig": "instagram",
    "fb": "facebook",
    "messenger.com": "messenger",
    "gmail": "email",
    "mail": "email",
    "text message": "sms",
}


def _resolve(platform: str) -> tuple[str, dict]:
    key = " ".join((platform or "").strip().lower().split())

    for tail in (" par", " pe", " on", " via", " me"):
        if key.endswith(tail):
            key = key[: -len(tail)].strip()

    key = ALIASES.get(key, key)

    if key in PLATFORMS:
        return key, PLATFORMS[key]

    from tools import browser

    url = browser.site_url(key)

    if url:
        return key, {"strategy": "web", "web": url}

    return key, {}


def _contacts() -> dict:
    if not CONTACTS.exists():
        return {}

    try:
        data = json.loads(CONTACTS.read_text(encoding="utf-8"))
    except Exception as error:
        logger.info("Contacts unreadable: %s", error)
        return {}

    return data if isinstance(data, dict) else {}


def _contact_entry(contact: str) -> dict:
    wanted = " ".join((contact or "").strip().lower().split())

    for name, fields in _contacts().items():
        if " ".join(name.lower().split()) == wanted:
            return fields if isinstance(fields, dict) else {}

    return {}


def _key(vk: int, up: bool = False) -> None:
    ctypes.windll.user32.keybd_event(vk, 0, 0x0002 if up else 0, 0)


class _RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


def _foreground() -> tuple[int, str]:
    """The window in front right now: its handle and its title."""

    user32 = ctypes.windll.user32
    hwnd = int(user32.GetForegroundWindow() or 0)
    length = int(user32.GetWindowTextLengthW(hwnd) or 0)
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)

    return hwnd, buffer.value


def _window_crop(path: str, hwnd: int, title: str) -> str:
    """Screenshot of just that window, so another app cannot fake a chat box."""

    from tools import screenshot as shots

    rect = _RECT()

    if not ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return path

    try:
        from PIL import Image

        with Image.open(path) as image:
            box = (
                max(0, rect.left),
                max(0, rect.top),
                min(image.width, rect.right),
                min(image.height, rect.bottom),
            )

            if box[2] - box[0] < 200 or box[3] - box[1] < 200:
                return path

            target = Path(path).with_name(Path(path).stem + "-window.png")
            image.crop(box).save(target, format="PNG")

        return str(target)
    except Exception as error:
        logger.info("Window crop skipped: %s", error)
        return path


def _title_matches(title: str, spec: dict) -> bool:
    wanted = [word.lower() for word in (spec.get("window") or ())]

    return any(word and word in (title or "").lower() for word in wanted)


def _tap(vk: int) -> None:
    _key(vk)
    _key(vk, up=True)


def _combo(*vks: int) -> None:
    for vk in vks:
        _key(vk)
    time.sleep(0.05)

    for vk in reversed(vks):
        _key(vk, up=True)


VK = {"ctrl": 0x11, "enter": 0x0D, "down": 0x28, "esc": 0x1B, "tab": 0x09}


def _focus(window_titles) -> bool:
    from tools import windows

    for title in window_titles:
        result = windows.focus_window(title)

        if result.get("success"):
            return True

    return False


def _chat_ready(shot_path: str) -> bool:
    """Is a conversation actually open? A login screen is not a chat."""

    if not shot_path:
        return False

    from tools import vision

    answer = vision.see(
        "Read this app window. If it shows a sign-in screen, a \"Log in\" button "
        "or a QR code, answer LOGIN. If it shows an open conversation with a "
        "text input box at the bottom, answer READY. Anything else: OTHER. "
        "Answer with one word only.",
        shot_path,
    )

    if not answer.get("success"):
        # Cannot check: assume the app is usable rather than block the send.
        return True

    verdict = (answer.get("answer") or "").strip().lower()

    return verdict.startswith("ready")


def _describe(platform: str, contact: str, text: str, sent: bool, detail: str) -> str:
    state = "Message sent" if sent else "Message typed but not sent"

    return f"{state} on {platform} to {contact}: “{text}”. {detail}".strip()


def _link_shortcut(fields: dict, spec: dict, text: str) -> str:
    """A deep link that opens the chat with the text already filled in."""

    template = spec.get("link") or ""

    if not template:
        return ""

    from urllib.parse import quote

    values = {
        "text": quote(text),
        "phone": "".join(ch for ch in str(fields.get("phone") or "") if ch.isdigit()),
        "username": str(fields.get("username") or fields.get("telegram") or "").lstrip("@"),
        "email": quote(str(fields.get("email") or "")),
    }

    if "{phone}" in template and not values["phone"]:
        return ""

    if "{username}" in template and not values["username"]:
        return ""

    if "{email}" in template and not values["email"]:
        return ""

    return template.format(**values)


def _open_link(link: str) -> bool:
    import os

    try:
        os.startfile(link)
        return True
    except Exception as error:
        logger.info("Link did not open: %s", error)
        return False


def _search_and_open(platform: str, spec: dict, contact: str) -> dict:
    """Bring the app forward and open the chat whose name matches `contact`."""

    from tools import apps, typing

    opened = apps.open_app(spec.get("app") or platform)

    time.sleep(1.8)

    focused = _focus(spec.get("window") or (platform,))
    time.sleep(0.6)

    hwnd, title = _foreground()

    # Typing into whatever happens to be focused is how a message lands in the
    # wrong app, so refuse unless the target window is really in front.
    if not focused or not _title_matches(title, spec):
        return {
            "success": False,
            "error": (
                f"{platform} is not in front"
                + (f" (the front window is \"{title}\")." if title else ".")
            ),
            "window": title,
            "opened": opened.get("message"),
        }

    # Ctrl+F opens the in-app search in WhatsApp and Telegram Desktop.
    _combo(VK["ctrl"], 0x46)
    time.sleep(0.7)
    typing.type_here(contact)
    time.sleep(1.1)
    _tap(VK["down"])
    time.sleep(0.25)
    _tap(VK["enter"])
    time.sleep(1.3)

    hwnd, title = _foreground()

    return {
        "success": True,
        "focused": focused,
        "app": opened.get("message"),
        "hwnd": hwnd,
        "title": title,
    }


def _web_chat(platform: str, spec: dict, contact: str) -> dict:
    """Open the site and let the screen agent find the chat."""

    from tools import browser, screen_agent

    opened = browser.open_website(spec.get("web") or "")

    if not opened.get("success", True):
        return {"success": False, "error": f"{platform} did not open."}

    time.sleep(3.0)

    walked = screen_agent.run_task(
        f"On {platform}, search for the person or chat called {contact} and open "
        f"the conversation with them. Do not send any message.",
        max_steps=3,
    )

    return {
        "success": bool(walked.get("success")),
        "opened": walked.get("finished", False),
        "error": walked.get("error"),
    }


def send_message(
    platform: str,
    contact: str,
    text: str,
    confirm: bool = False,
) -> dict:
    """Message `contact` on `platform`; only press send when `confirm` is true."""

    platform_key, spec = _resolve(platform)
    text = (text or "").strip()
    contact = (contact or "").strip()

    if not contact:
        return {"success": False, "error": "Which contact should I message?"}

    if not text:
        return {"success": False, "error": "What should the message say?"}

    if not spec:
        return {
            "success": False,
            "error": f"I don't know how to message on {platform} yet.",
            "platforms": sorted(PLATFORMS),
        }

    fields = _contact_entry(contact)
    strategy = spec.get("strategy") or "web"
    link = _link_shortcut(fields, spec, text)

    if strategy == "link" or (link and strategy != "web"):
        if link and _open_link(link):
            time.sleep(2.2)

            from tools import screenshot

            shot = screenshot.capture_screen("message-chat", persist=False)

            if not _chat_ready(shot.get("path") or ""):
                return {
                    "success": False,
                    "platform": platform_key,
                    "contact": contact,
                    "text": text,
                    "sent": False,
                    "screen": shot.get("path"),
                    "error": (
                        f"No chat is open on {platform_key}: it looks signed out. "
                        f"Open it and log in once, then ask again."
                    ),
                }

            if confirm:
                _tap(VK["enter"])

            return {
                "success": True,
                "platform": platform_key,
                "contact": contact,
                "text": text,
                "sent": bool(confirm),
                "via": "link",
                "message": _describe(
                    platform_key,
                    contact,
                    text,
                    bool(confirm),
                    "Opened with the chat filled in.",
                ),
            }

        if strategy == "link":
            return {
                "success": False,
                "error": f"No {platform_key} address for {contact} in data/contacts.json.",
            }

    if strategy == "search":
        result = _search_and_open(platform_key, spec, contact)

        # No desktop app (or it would not come forward): use the website.
        if not result.get("success"):
            result = _web_chat(platform_key, spec, contact)
            strategy = "web"

        if not result.get("success"):
            return {
                "success": False,
                "error": result.get("error"),
                "hint": f"Is {platform_key} installed, or signed in on the web?",
            }
    else:
        result = _web_chat(platform_key, spec, contact)

        if not result.get("success"):
            return {
                "success": False,
                "error": result.get("error") or f"Could not reach the chat on {platform_key}.",
            }

    hwnd, title = _foreground()

    if spec.get("window") and not _title_matches(title, spec):
        return {
            "success": False,
            "platform": platform_key,
            "contact": contact,
            "text": text,
            "sent": False,
            "error": f"{platform_key} lost the foreground to \"{title}\", so I did not type anything.",
        }

    from tools import screenshot

    before = screenshot.capture_screen("message-chat", persist=False)
    view = _window_crop(before.get("path") or "", hwnd, title)

    if not _chat_ready(view):
        return {
            "success": False,
            "platform": platform_key,
            "contact": contact,
            "text": text,
            "sent": False,
            "screen": view,
            "error": (
                f"No chat is open on {platform_key}: it looks signed out. Open it "
                f"and log in once, then ask again."
            ),
        }

    from tools import typing

    # The clipboard write happens in another process: make sure the chat is
    # still in front before pasting into it.
    if spec.get("window") and not _title_matches(_foreground()[1], spec):
        _focus(spec.get("window") or (platform_key,))
        time.sleep(0.4)

    typing.type_here(text)
    time.sleep(0.5)

    shot = screenshot.capture_screen("message", persist=False)

    if confirm:
        _tap(VK["enter"])
        time.sleep(0.4)

    return {
        "success": True,
        "platform": platform_key,
        "contact": contact,
        "text": text,
        "sent": bool(confirm),
        "via": strategy,
        "screen": shot.get("path"),
        "message": _describe(
            platform_key,
            contact,
            text,
            bool(confirm),
            "" if confirm else "Say send and I'll press enter.",
        ),
    }
