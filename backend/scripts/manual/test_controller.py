import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from controllers.voice_controller import VoiceController


controller = VoiceController()

controller.start()