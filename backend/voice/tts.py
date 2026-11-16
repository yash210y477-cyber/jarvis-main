import asyncio
import hashlib
import os
import shutil
import tempfile
import threading
import time
from pathlib import Path

import edge_tts

from voice import speech

# pygame opens the sound card and pulls in SDL; it is imported the first time a
# sentence is actually spoken.
pygame = None


def _pygame():
    """The pygame module, imported once on the first spoken sentence."""

    global pygame

    if pygame is None:

        # The banner is noise in the log; the message itself still comes through.
        os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

        import pygame as module

        pygame = module

    return pygame



BACKEND = Path(__file__).resolve().parents[1]


class TextToSpeech:

    def __init__(self):

        self.voice = os.getenv("TTS_VOICE", "en-US-AndrewMultilingualNeural")

        # A voice picked in Settings stays picked after a restart.
        try:
            saved = (BACKEND / "data" / "voice.txt").read_text(encoding="utf-8").strip()

            if saved:
                self.voice = saved
        except Exception:
            pass

        self.current_file = None

        self.stop_requested = False

        self.lock = threading.Lock()

        self.initialized = False

        self._init_audio()

    # ---------------------------------
    # INITIALIZE AUDIO
    # ---------------------------------

    def _init_audio(self):

        try:

            _pygame().mixer.init()

            self.initialized = True

        except Exception as e:

            print("Audio Init Error:", e)

    # ---------------------------------
    # GENERATE AUDIO
    # ---------------------------------

    async def _generate(self, text, filename):

        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice
        )

        await communicate.save(filename)

    # ---------------------------------
    # SPEAK
    # ---------------------------------

    def set_voice(self, name):
        """Switch voice for the next sentence, no restart needed."""

        name = (name or "").strip()

        if not name:
            return self.voice

        if name == "default":
            self.voice = self.default_voice

            try:
                (BACKEND / "data" / "voice.txt").unlink(missing_ok=True)
            except Exception:
                pass

            return self.voice

        if name == self.voice:
            return self.voice

        self.voice = name

        try:
            (BACKEND / "data").mkdir(parents=True, exist_ok=True)
            (BACKEND / "data" / "voice.txt").write_text(name, encoding="utf-8")
        except Exception:
            pass

        return self.voice

    @property
    def default_voice(self):
        """The voice the app ships with, before any choice is made."""

        return os.getenv("TTS_VOICE", "en-US-AndrewMultilingualNeural")

    def speak(self, text):

        if not text:
            return

        pieces = speech.plan(text, self.voice, speech.HINDI_MALE, speech.HINDI_FEMALE)

        if not pieces:
            return

        original = self.voice

        try:
            for voice_name, chunk in pieces:
                if self.stop_requested:
                    break

                self.voice = voice_name
                self._speak_chunk(chunk)
        finally:
            self.voice = original

    def _speak_chunk(self, text):

        if not text:
            return

        if not self.initialized:

            self._init_audio()

            if not self.initialized:
                return

        filename = None

        cached = self._cached_path(text)

        with self.lock:

            self.stop_requested = False

        try:

            if cached and cached.exists() and cached.stat().st_size > 1024:

                _pygame().mixer.music.load(str(cached))

                _pygame().mixer.music.play()

                self._wait_until_done()

                return

            temp = tempfile.NamedTemporaryFile(
                suffix=".mp3",
                delete=False
            )

            filename = temp.name

            temp.close()

            self.current_file = filename

            # Generate TTS
            asyncio.run(
                self._generate(
                    text,
                    filename
                )
            )

            # Interrupted while generating
            if self.stop_requested:

                return

            # Keep the clip so the next identical line plays instantly.
            try:

                cached.parent.mkdir(parents=True, exist_ok=True)

                shutil.copyfile(filename, cached)

            except Exception:

                pass

            _pygame().mixer.music.load(filename)

            _pygame().mixer.music.play()

            # Wait while audio is playing
            while _pygame().mixer.music.get_busy():

                if self.stop_requested:

                    _pygame().mixer.music.stop()

                    break

                time.sleep(0.03)

        except Exception as e:

            print("TTS Error:", e)

        finally:

            try:

                _pygame().mixer.music.stop()

            except Exception:

                pass

            self.current_file = None

            if filename:

                try:

                    if os.path.exists(filename):

                        os.remove(filename)

                except Exception:

                    pass

    def _cached_path(self, text):

        key = hashlib.md5(f"{self.voice}:{text}".encode("utf-8")).hexdigest()

        return Path("data/tts_cache") / f"{key}.mp3"

    def _wait_until_done(self):

        while _pygame().mixer.music.get_busy():

            if self.stop_requested:

                _pygame().mixer.music.stop()

                break

            time.sleep(0.03)

    # ---------------------------------
    # STOP SPEAKING
    # ---------------------------------

    def stop(self):

        with self.lock:

            self.stop_requested = True

        try:

            if self.initialized:

                _pygame().mixer.music.stop()

        except Exception as e:

            print(
                "TTS Stop Error:",
                e
            )

    # ---------------------------------
    # CLEANUP
    # ---------------------------------

    def cleanup(self):

        self.stop()

        try:

            if self.initialized:

                _pygame().mixer.quit()

                self.initialized = False

        except Exception:

            pass