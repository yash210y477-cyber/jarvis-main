from fastapi import APIRouter

from controllers.command_controller import CommandController
from voice.engine import VoiceEngine

router = APIRouter()

voice = VoiceEngine()
command = CommandController()


@router.post("/voice")
def voice_command():

    text = voice.listen()

    response = command.execute(text)

    response["heard"] = text

    return response