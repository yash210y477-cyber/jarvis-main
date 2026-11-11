
from fastapi import APIRouter

from controllers.command_controller import CommandController
from voice.engine import Engine

router = APIRouter()

voice = Engine()
command = CommandController()


@router.post("/voice")
def voice_command():

    text = voice.listen()

    if not text:
        return {
            "heard": None,
            "response": "I couldn't hear anything. Please try again."
        }

    response = command.execute(text)

    response["heard"] = text

    return response
