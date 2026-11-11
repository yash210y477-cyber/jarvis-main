"""Screenshot capture through PowerShell/.NET (no extra dependency)."""

import subprocess
from datetime import datetime
from pathlib import Path

from config.settings import settings


SCREENSHOT_DIR = Path(settings.WORKSPACE_ROOT) / "backend" / "data" / "screenshots"

SCRIPT = """
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bitmap = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
$bitmap.Save('{path}', [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose()
$bitmap.Dispose()
"""


def capture_screen(label: str = "") -> dict:

    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    safe = "".join(
        char for char in (label or "").strip().lower().replace(" ", "-")
        if char.isalnum() or char == "-"
    )[:40]

    name = f"screenshot-{stamp}{'-' + safe if safe else ''}.png"

    target = SCREENSHOT_DIR / name

    try:

        completed = subprocess.run(
            [
                "powershell", "-NoProfile", "-NonInteractive", "-Command",
                SCRIPT.replace("{path}", str(target)),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

    except Exception as error:

        return {"success": False, "error": str(error)}

    if completed.returncode != 0 or not target.exists():

        return {
            "success": False,
            "error": (completed.stderr or "Screenshot failed.").strip(),
        }

    return {
        "success": True,
        "path": str(target),
        "file": name,
        "bytes": target.stat().st_size,
    }
