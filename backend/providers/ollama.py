import requests


class OllamaProvider:

    def __init__(self):

        self.url = "http://127.0.0.1:11434/api/generate"
        self.model = "qwen3:8b"

    def chat(self, prompt: str):

        try:

            response = requests.post(

                self.url,

                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },

                timeout=120

            )

            response.raise_for_status()

            data = response.json()

            return {

                "success": True,

                "provider": "ollama",

                "response": data.get("response", "")

            }

        except Exception as e:

            return {

                "success": False,

                "provider": "ollama",

                "error": str(e)

            }