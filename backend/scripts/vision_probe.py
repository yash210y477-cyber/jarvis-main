"""Which configured provider can actually see? Tries z.ai, Groq and OpenRouter."""

import base64
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

image = Path(__file__).resolve().parents[1] / "data" / "screenshots" / "vision-probe.png"
data = base64.b64encode(image.read_bytes()).decode("ascii")
url = f"data:image/png;base64,{data}"

CANDIDATES = [
    ("groq", "https://api.groq.com/openai/v1", "GROQ_API_KEY",
     ["meta-llama/llama-4-scout-17b-16e-instruct", "meta-llama/llama-4-maverick-17b-128e-instruct"]),
    ("openrouter", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY",
     ["google/gemini-2.0-flash-exp:free", "qwen/qwen2.5-vl-72b-instruct:free"]),
    ("deepseek", "https://api.deepseek.com", "DEEPSEEK_API_KEY", ["deepseek-chat"]),
]


def probe(name, base_url, key_name, models):
    key = (os.getenv(key_name) or "").strip()

    if not key:
        print(f"{name}: no key")
        return

    client = OpenAI(api_key=key, base_url=base_url, timeout=60)

    for model in models:
        try:
            reply = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "What text is in this image?"},
                            {"type": "image_url", "image_url": {"url": url}},
                        ],
                    }
                ],
                max_tokens=60,
            )
            text = (reply.choices[0].message.content or "").strip()
            print(f"{name}/{model}: OK -> {text[:80]!r}")
            return
        except Exception as error:
            print(f"{name}/{model}: {str(error)[:140]}")


for candidate in CANDIDATES:
    probe(*candidate)
