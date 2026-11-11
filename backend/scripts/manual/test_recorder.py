import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from voice.recorder import Recorder


recorder = Recorder()

file = recorder.record()

print()

print(file)