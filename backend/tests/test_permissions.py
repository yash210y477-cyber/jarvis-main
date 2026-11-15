"""Nothing touches the screen or the user's folders without their permission."""

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SCREEN_TOOLS = (
    "screenshot",
    "read_screen",
    "ask_area",
    "screen_task",
    "companion_start",
    "screen_watch_start",
)


def test_every_screen_tool_asks_first():
    from tools.builtin import build_registry

    registry = build_registry()

    for name in SCREEN_TOOLS:

        assert registry.get(name)["permission"] == "confirm", name


def test_a_generated_picture_is_never_opened_or_saved_on_its_own():
    from tools import image_gen

    parameters = inspect.signature(image_gen.generate_image).parameters
    source = inspect.getsource(image_gen.generate_image)

    assert "show" not in parameters
    assert "startfile" not in source
    assert "save_to_downloads" not in source


def test_only_the_download_button_copies_a_picture_into_downloads():
    from api import files
    from tools import image_gen

    # The Downloads folder is touched by the download endpoints only.
    assert "download" in inspect.getsource(image_gen.save_to_downloads)
    assert "download" in inspect.getsource(files.download_file)
