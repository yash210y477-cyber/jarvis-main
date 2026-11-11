import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from voice.engine import VoiceEngine

voice = VoiceEngine()

text = voice.listen()

print()

print("You said:")

print(text)

voice.speak(
    f"You said {text}"
)