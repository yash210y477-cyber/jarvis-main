"""Run every safe JARVIS tool once so a broken handler shows up immediately.

    ./.venv/Scripts/python.exe tool_check.py

Destructive tools (power, lock, close-everything, shell) are skipped on purpose;
they are listed at the end so the report stays honest about what was not run.
"""

import time

from tools import builtin

SKIP = {
    "power_action", "lock_screen", "close_all_windows", "run_command",
    "shutdown", "restart", "sleep", "signout",
}

SAMPLES = {
    "open_app": {"app_name": "calculator"},
    "close_app": {"app_name": "calculator"},
    "system_status": {},
    "get_datetime": {"part": "time"},
    "screenshot": {"label": "tool_check"},
    "get_clipboard": {},
    "set_clipboard": {"text": "jarvis tool check"},
    "list_files": {"path": "."},
    "read_file": {"path": "requirements.txt"},
    "list_windows": {},
    "minimize_all": {},
    "media_control": {"action": "volume_up", "steps": 1},
    "get_volume": {},
    "set_volume": {"percent": 40},
    "open_special": {"app": "calculator"},
    "open_path": {"path": "downloads folder"},
    "notify": {"title": "JARVIS", "message": "tool check"},
    "set_timer": {"seconds": 2, "label": "tool check"},
    "list_timers": {},
    "cancel_timer": {},
    "set_reminder": {"text": "tool check", "when": "in 5 minutes"},
    "list_reminders": {},
    "cancel_reminder": {},
    "search_site": {"query": "python", "site": "google"},
    "open_website": {"url": "example.com"},
    "open_site": {"name": "youtube"},
    "browser_control": {"action": "new_tab"},
    "focus_window": {"title": "Calculator"},
    "minimize_window": {"title": "Calculator"},
    "search_web": {"query": "python tutorials"},
    "write_file": {"path": "data/tool_check.txt", "content": "ok"},
}


def main():

    registry = builtin.REGISTRY.tools
    executor = builtin.EXECUTOR

    passed, failed, skipped = [], [], []

    for name in sorted(registry):

        if name in SKIP:
            skipped.append((name, "destructive"))
            continue

        args = SAMPLES.get(name)

        if args is None:
            skipped.append((name, "no sample args"))
            continue

        started = time.time()

        try:
            result = executor.execute(name, **args)
            ok = bool(result.get("success"))
            note = "" if ok else (result.get("error") or str(result))[:80]
        except Exception as error:  # a crash is a failure, never a skip
            ok, note = False, f"{type(error).__name__}: {error}"[:80]

        took = time.time() - started

        if ok:
            passed.append((name, took))
        else:
            failed.append((name, took, note))

    print(f"\nJARVIS tool check: {len(passed)} passed, {len(failed)} failed, "
          f"{len(skipped)} skipped\n")

    for name, took in passed:
        print(f"  PASS  {name:20} {took:5.2f}s")

    for name, took, note in failed:
        print(f"  FAIL  {name:20} {took:5.2f}s  {note}")

    for name, reason in skipped:
        print(f"  SKIP  {name:20} {reason}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
