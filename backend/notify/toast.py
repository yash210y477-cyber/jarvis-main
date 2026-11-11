"""Windows toast notifications through the built-in WinRT API.

PowerShell is always present on Windows, so this needs no pip package.
"""

import html
import subprocess
import sys

from config.settings import settings


SCRIPT = """
$ErrorActionPreference = "Stop"
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml("<toast><visual><binding template='ToastGeneric'><text>{title}</text><text>{body}</text></binding></visual></toast>")
$toast = New-Object Windows.UI.Notifications.ToastNotification $xml
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("{app}").Show($toast)
"""


def _escape(text: str) -> str:

    return html.escape((text or "").strip(), quote=False)[:400]


def notify(title="JARVIS", message="", app="JARVIS"):

    if not getattr(settings, "NOTIFICATIONS_ENABLED", True):

        return {
            "success": False,
            "title": title,
            "message": message,
            "error": "Notifications are disabled in settings.",
        }

    if sys.platform != "win32":

        return {
            "success": False,
            "title": title,
            "message": message,
            "error": "Toast notifications need Windows.",
        }

    script = SCRIPT.format(
        title=_escape(title),
        body=_escape(message),
        app=_escape(app) or "JARVIS",
    )

    try:

        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            timeout=25,
        )

    except Exception as error:

        return {
            "success": False,
            "title": title,
            "message": message,
            "error": str(error),
        }

    ok = result.returncode == 0

    return {
        "success": ok,
        "title": title,
        "message": message,
        "error": None if ok else (result.stderr or "").strip()[:300],
    }
