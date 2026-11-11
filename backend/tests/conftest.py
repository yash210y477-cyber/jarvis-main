import os
import sys
import tempfile
from pathlib import Path


BACKEND = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(BACKEND))

# Must be set before config.settings is imported anywhere.
os.environ["JARVIS_DATA_DIR"] = tempfile.mkdtemp(prefix="jarvis-tests-")

os.environ["JARVIS_LOCAL_TOKEN"] = ""
