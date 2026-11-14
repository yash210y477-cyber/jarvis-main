"""Run one guided walkthrough step for real: ring the target, wait, screenshot."""

import threading
import time

from tools import apps, screen_agent, screenshot, windows

print("open  :", apps.open_app("notepad")["message"])
time.sleep(2.5)
print("focus :", windows.focus_window("notepad").get("window"))
time.sleep(0.8)

result = {}

def run():
    result.update(
        screen_agent.run_task("Show me where the File menu is", guided=True, max_steps=1)
    )

worker = threading.Thread(target=run, daemon=True)
started = time.time()
worker.start()

# Give the vision model time to plan, then photograph the ring.
time.sleep(12)
shot = screenshot.capture_screen("guided-ring")
print("ring shot:", shot["path"])
print("ring location:", [s.get("detail") for s in result.get("steps", [])])

worker.join(timeout=90)

print("elapsed:", round(time.time() - started, 1), "s")
print("guided:", result.get("guided"), "| finished:", result.get("finished"))
for step in result.get("steps", []):
    print("  step", step.get("step"), step.get("action"), "->", step.get("detail"))

apps.close_app("notepad")
