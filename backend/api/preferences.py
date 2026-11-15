"""Reply language: the choice made in Settings, kept across restarts."""

from fastapi import APIRouter

from brain import language

router = APIRouter()


@router.get("/language")
def get_language():
    """The mode in use and the three choices Settings offers."""

    return {
        "success": True,
        "mode": language.current(),
        "options": language.options(),
    }


@router.post("/language")
def set_language(data: dict):
    """Pick auto, english or hinglish."""

    try:
        mode = language.set_language(data.get("mode"))
    except ValueError as error:
        return {
            "success": False,
            "error": str(error),
            "options": [item["id"] for item in language.options()],
        }

    return {"success": True, "mode": mode}
