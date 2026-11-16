"""The REA/Node runtime folder must be configurable and safe by default.

Moving the bundled runtime out of the repository keeps 24,000 files away from
editors, watchers and virus scans, but an install that never sets
JARVIS_TOOLS_DIR must keep finding it under backend/data/tools.
"""

import os
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]

PROBE = (
    "import sys; sys.path.insert(0, '.'); "
    "from config.settings import settings; "
    "from tools import reverse_engineer as rea; "
    "print(settings.TOOLS_DIR); print(rea.TOOLS); print(rea.NODE)"
)


def _paths(tools_dir: str) -> list[str]:
    env = {key: value for key, value in os.environ.items() if key != "JARVIS_TOOLS_DIR"}
    env["JARVIS_TOOLS_DIR"] = tools_dir
    env["PYTHONIOENCODING"] = "utf-8"

    finished = subprocess.run(
        [sys.executable, "-c", PROBE],
        cwd=str(BACKEND),
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )

    assert finished.returncode == 0, finished.stderr

    return finished.stdout.strip().splitlines()


def test_without_the_variable_tools_stay_under_data(tmp_path):
    settings_dir, rea_dir, node = _paths("")

    assert Path(settings_dir) == BACKEND / "data" / "tools"
    assert Path(rea_dir) == BACKEND / "data" / "tools"
    assert node.startswith(settings_dir)


def test_the_variable_moves_tools_and_the_node_runtime(tmp_path):
    wanted = tmp_path / "jarvis-tools"

    settings_dir, rea_dir, node = _paths(str(wanted))

    assert Path(settings_dir) == wanted
    assert Path(rea_dir) == wanted
    assert Path(node) == wanted / "node-v24.22.3-win-x64" / "node.exe"
