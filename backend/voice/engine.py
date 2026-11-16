import threading

class VoiceEngine:

    def __init__(self):

        self._recorder = None
        self._stt = None
        self._tts = None

        self.speaking = False
        self.speak_lock = threading.Lock()

    # torch, faster-whisper and pygame cost seconds of CPU and hundreds of
    # megabytes, and most chats never touch the microphone or the speaker, so
    # each piece is built on first use.

    @property
    def recorder(self):

        if self._recorder is None:

            from voice.recorder import Recorder

            self._recorder = Recorder()

        return self._recorder

    @property
    def stt(self):

        if self._stt is None:

            from voice.stt import SpeechToText

            self._stt = SpeechToText()

        return self._stt

    @property
    def tts(self):

        if self._tts is None:

            from voice.tts import TextToSpeech

            self._tts = TextToSpeech()

        return self._tts

    # ---------------------------------
    # LISTEN
    # ---------------------------------

    def listen(self):

        try:

            # Don't listen while Jarvis is speaking
            if self.speaking:
                return None

            audio = self.recorder.record()

            if not audio:
                return None

            return audio

        except Exception as e:

            print("Listen Error:", e)

            return None

    # ---------------------------------
    # TRANSCRIBE
    # ---------------------------------

    def transcribe(self, audio):

        try:

            if not audio:
                return ""

            return self.stt.transcribe(audio)

        except Exception as e:

            print("STT Error:", e)

            return ""

    # ---------------------------------
    # SPEAK
    # ---------------------------------

    def speak(self, text):

        if not text:
            return

        with self.speak_lock:

            try:

                self.speaking = True

                self.tts.speak(text)

            except Exception as e:

                print("TTS Error:", e)

            finally:

                self.speaking = False

    # ---------------------------------
    # INTERRUPT TTS
    # ---------------------------------

    def stop_speaking(self):

        try:

            if self._tts is not None:

                self._tts.stop()

        except Exception as e:

            print(
                "TTS Stop Error:",
                e
            )

        finally:

            self.speaking = False

    # ---------------------------------
    # STOP RECORDING
    # ---------------------------------

    def stop(self):

        try:

            if self._recorder is not None:

                self._recorder.stop()

        except Exception as e:

            print(
                "Recorder Stop Error:",
                e
            )

        self.stop_speaking()