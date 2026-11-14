"""Run the answer card script once and show whether the window survives."""

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from tools import card

payload = Path(tempfile.gettempdir()) / "card-probe.json"
payload.write_text(
    json.dumps(
        {"title": "probe", "body": "hello", "seconds": 5, "width": 300, "side": "right"}
    ),
    encoding="utf-8",
)

script = card.CARD_SCRIPT.replace("{payload}", str(payload).replace("\\", "\\\\"))

process = subprocess.Popen(
    [sys.executable, "-c", script],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
)

time.sleep(2.5)

if process.poll() is None:
    print("alive after 2.5s: True")
    process.terminate()
else:
    out, err = process.communicate()
    print("alive after 2.5s: False")
    print("stderr:", (err or "")[:800])
