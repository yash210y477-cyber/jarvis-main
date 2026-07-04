import asyncio
import os
import tempfile

import edge_tts


class TextToSpeech:

    def __init__(self):

        self.voice = "en-US-GuyNeural"

    async def _generate(self, text, filename):

        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice
        )

        await communicate.save(filename)

    def speak(self, text):

        with tempfile.NamedTemporaryFile(
            suffix=".mp3",
            delete=False
        ) as file:

            filename = file.name

        asyncio.run(
            self._generate(
                text,
                filename
            )
        )

        os.startfile(filename)