from fastapi import APIRouter

from controllers.command_controller import CommandController
from voice.engine import VoiceEngine

router = APIRouter()

voice = VoiceEngine()
command = CommandController()


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
