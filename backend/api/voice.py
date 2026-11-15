from fastapi import APIRouter

from config.settings import settings
from controllers.command_controller import CommandController
from voice.engine import VoiceEngine

router = APIRouter()

voice = VoiceEngine()
command = CommandController()

SAMPLE = "Namaste Yash. Main Jarvis hoon, aapka personal assistant. Ye meri awaaz hai."


@router.post("/voice")
def voice_command():
    """Record one utterance, transcribe it and run the command."""

    text = voice.transcribe(voice.listen())

    if not text:
        return {
            "heard": None,
            "response": "I couldn't hear anything. Please try again."
        }

    response = command.execute(text)

    response["heard"] = text

    return response


@router.get("/voice/options")
def voice_options():
    """The six voices Settings offers, plus the one in use."""

    return {
        "success": True,
        "current": voice.tts.voice,
        "voices": list(settings.VOICE_OPTIONS),
    }


@router.post("/voice/voice")
def set_voice(data: dict):
    """Pick one of the offered voices; it is used from the next sentence."""

    wanted = (data.get("voice") or "").strip()
    allowed = {item["id"] for item in settings.VOICE_OPTIONS}

    if wanted not in allowed:
        return {
            "success": False,
            "error": "That voice is not one of the six options.",
            "voices": [item["id"] for item in settings.VOICE_OPTIONS],
        }

    return {"success": True, "current": voice.tts.set_voice(wanted)}


@router.post("/voice/preview")
def preview_voice(data: dict):
    """Say a sample line in a voice, so the choice can be heard first."""

    wanted = (data.get("voice") or voice.tts.voice).strip()
    allowed = {item["id"] for item in settings.VOICE_OPTIONS}

    if wanted not in allowed:
        return {"success": False, "error": "That voice is not one of the six options."}

    text = (data.get("text") or SAMPLE).strip()
    previous = voice.tts.voice

    try:
        voice.tts.set_voice(wanted)
        voice.tts.speak(text)
    except Exception as error:
        return {"success": False, "error": str(error)}
    finally:
        voice.tts.set_voice(previous)

    return {"success": True, "voice": wanted, "text": text}
