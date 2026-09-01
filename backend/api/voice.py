from fastapi import APIRouter
from controllers.voice_controller import VoiceController

router = APIRouter(
    prefix="/voice",
    tags=["Voice"]
)

controller = VoiceController()


# -------------------------
# Single Voice Command
# -------------------------
@router.post("")
def voice():

    return controller.start()


# -------------------------
# Continuous Voice Mode
# -------------------------
@router.post("/live")
def start_live():

    return controller.start_continuous()


# -------------------------
# Stop Voice Mode
# -------------------------
@router.post("/stop")
def stop_live():

    return controller.stop()


# -------------------------
# Voice Status
# -------------------------
@router.get("/status")
def status():

    return {
        "running": controller.running
    }