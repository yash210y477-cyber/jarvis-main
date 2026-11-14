"""Screenshot capture through PowerShell/.NET (no extra dependency).

The capture has to be DPI aware: a process that is not sees a scaled-down
desktop on a 125%/150% display and CopyFromScreen copies only that smaller box,
which looked like the screenshot being cropped. The script therefore turns DPI
awareness on first, then copies the whole virtual screen (every monitor).
"""

import subprocess
from datetime import datetime
from pathlib import Path

from config.settings import settings


SCREENSHOT_DIR = Path(settings.WORKSPACE_ROOT) / "backend" / "data" / "screenshots"

SCRIPT = r"""
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
Add-Type -TypeDefinition @'
using System.Runtime.InteropServices;
public class JarvisDpi {
    [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
    [DllImport("shcore.dll")] public static extern int SetProcessDpiAwareness(int value);
}
'@
try { [JarvisDpi]::SetProcessDpiAwareness(2) | Out-Null } catch { [JarvisDpi]::SetProcessDPIAware() | Out-Null }
$bounds = [System.Windows.Forms.SystemInformation]::VirtualScreen
$bitmap = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
$bitmap.Save('{path}', [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose()
$bitmap.Dispose()
Write-Output ("{0}x{1}+{2}+{3}" -f $bounds.Width, $bounds.Height, $bounds.X, $bounds.Y)
"""


def _enable_dpi_awareness():

    try:

        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(2)

    except Exception:

        pass


def capture_screen(label: str = "") -> dict:
    """Grab the whole virtual desktop and return its path and pixel bounds."""

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
                "powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden",
                "-Command", SCRIPT.replace("{path}", str(target)),
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

    result = {
        "success": True,
        "path": str(target),
        "file": name,
        "bytes": target.stat().st_size,
    }

    # "2560x1440+0+0" tells the caller where the picture sits in the desktop,
    # which matters for clicks when a second monitor is left of the main one.
    bounds = (completed.stdout or "").strip().splitlines()

    if bounds:

        try:

            size, left, top = bounds[-1].split("+", 1)[0], bounds[-1].split("+")[1], bounds[-1].split("+")[2]

            width, height = size.split("x")

            result.update(
                {
                    "width": int(width),
                    "height": int(height),
                    "left": int(left),
                    "top": int(top),
                }
            )

        except (ValueError, IndexError):

            pass

    return result
