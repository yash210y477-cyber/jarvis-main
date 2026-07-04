import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from voice.tts import TextToSpeech

tts = TextToSpeech()

tts.speak(
    "Hello Yash. I am Jarvis. How can I help you today?"
)