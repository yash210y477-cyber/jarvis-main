import sys
from pathlib import Path

# Add backend folder to Python path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from voice.recorder import Recorder
from voice.stt import SpeechToText


print("=" * 50)
print("JARVIS STT TEST")
print("=" * 50)

print("\n[STEP 1] Creating Recorder...")
recorder = Recorder()
print("✅ Recorder Ready")

print("\n[STEP 2] Loading Whisper Model...")
stt = SpeechToText()
print("✅ Whisper Ready")

print("\n[STEP 3] Recording Audio...")
audio_file = recorder.record()
print(f"✅ Audio Saved: {audio_file}")

print("\n[STEP 4] Transcribing...")
text = stt.transcribe(audio_file)
print("✅ Transcription Complete")

print("\n" + "=" * 50)
print("YOU SAID:")
print(text)
print("=" * 50)