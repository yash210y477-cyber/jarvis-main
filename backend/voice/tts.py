import asyncio
import os
import tempfile
import threading
import time

import edge_tts
import pygame


class TextToSpeech:

    def __init__(self):

        self.voice = "en-US-GuyNeural"

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

            pygame.mixer.init()

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

    def speak(self, text):

        if not text:
            return

        if not self.initialized:

            self._init_audio()

            if not self.initialized:
                return

        filename = None

        with self.lock:

            self.stop_requested = False

        try:

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

            pygame.mixer.music.load(filename)

            pygame.mixer.music.play()

            # Wait while audio is playing
            while pygame.mixer.music.get_busy():

                if self.stop_requested:

                    pygame.mixer.music.stop()

                    break

                time.sleep(0.03)

        except Exception as e:

            print("TTS Error:", e)

        finally:

            try:

                pygame.mixer.music.stop()

            except Exception:

                pass

            self.current_file = None

            if filename:

                try:

                    if os.path.exists(filename):

                        os.remove(filename)

                except Exception:

                    pass

    # ---------------------------------
    # STOP SPEAKING
    # ---------------------------------

    def stop(self):

        with self.lock:

            self.stop_requested = True

        try:

            if self.initialized:

                pygame.mixer.music.stop()

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

                pygame.mixer.quit()

                self.initialized = False

        except Exception:

            pass