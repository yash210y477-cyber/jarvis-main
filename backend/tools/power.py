"""Screen lock and power actions.

Shutdown, restart and sleep are confirm-level tools, so they only run after the
user types yes.
"""

import ctypes
import subprocess


ACTIONS = ("lock", "sleep", "shutdown", "restart", "signout")


def lock_screen():

    try:

        ctypes.windll.user32.LockWorkStation()

    except Exception as error:

        return {"success": False, "action": "lock", "error": str(error)}

    return {
        "success": True,
        "action": "lock",
        "message": "Locking the screen.",
    }


def power_action(action="lock"):

    action = (action or "").strip().lower()

    aliases = {
        "shut down": "shutdown",
        "power off": "shutdown",
        "poweroff": "shutdown",
        "reboot": "restart",
        "suspend": "sleep",
        "log out": "signout",
        "logout": "signout",
    }

    action = aliases.get(action, action)

    if action not in ACTIONS:

        return {
            "success": False,
            "error": f"Unknown power action: {action}",
        }

    if action == "lock":

        return lock_screen()

    try:

        if action == "sleep":

            subprocess.Popen(
                ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
                shell=False,
            )

            message = "Going to sleep."

        elif action == "shutdown":

            subprocess.Popen(["shutdown", "/s", "/t", "10"], shell=False)

            message = "Shutting down in 10 seconds. Run 'shutdown /a' to cancel."

        elif action == "restart":

            subprocess.Popen(["shutdown", "/r", "/t", "10"], shell=False)

            message = "Restarting in 10 seconds. Run 'shutdown /a' to cancel."

        else:

            subprocess.Popen(["shutdown", "/l"], shell=False)

            message = "Signing out."

    except Exception as error:

        return {"success": False, "action": action, "error": str(error)}

    return {"success": True, "action": action, "message": message}
