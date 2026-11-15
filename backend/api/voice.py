from fastapi import APIRouter

from config.settings import settings
from controllers.command_controller import CommandController
from voice.engine import VoiceEngine

router = APIRouter()

voice = VoiceEngine()
command = CommandController()

SAMPLE = "Hello Yash. I'm Jarvis, your personal assistant. This is how I sound."

DEFAULT = {
    "id": "default",
    "name": "Default",
    "gender": "",
    "accent": "system default voice",
}


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
        "default": voice.tts.default_voice,
        "voices": [DEFAULT] + list(settings.VOICE_OPTIONS),
    }


@router.post("/voice/voice")
def set_voice(data: dict):
    """Pick one of the offered voices; it is used from the next sentence."""

    wanted = (data.get("voice") or "").strip()
    allowed = {"default"} | {item["id"] for item in settings.VOICE_OPTIONS}

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
    allowed = {"default"} | {item["id"] for item in settings.VOICE_OPTIONS}

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


@router.post("/voice/say")
def say(data: dict):
    """Speak a line in the confirmed voice (this is how Mina talks)."""

    text = (data.get("text") or "").strip()

    if not text:
        return {"success": False, "error": "Nothing to say."}

    try:
        voice.tts.speak(text[:1500])
    except Exception as error:
        return {"success": False, "error": str(error)}

    return {"success": True, "voice": voice.tts.voice}


@router.post("/voice/stop")
def stop_speaking():
    """Stop whatever is being said right now."""

    voice.tts.stop_speaking()

    return {"success": True}
