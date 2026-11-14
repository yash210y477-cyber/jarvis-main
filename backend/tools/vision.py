"""Look at a picture with whichever vision model can answer right now.

z.ai is preferred, but its vision models need a paid balance. When that fails
the request falls back to the free vision models OpenRouter serves, so screen
reading keeps working without a recharge.
"""

import base64
import logging
import os
from pathlib import Path

from openai import OpenAI

from config.settings import settings
from providers.zai import ZaiProvider

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1"

FALLBACK_MODELS = (
    "inclusionai/ling-3.2-flash:free",
    "nvidia/nemotron-3.5-super-vl:free",
    "particle-ai/particle-1:free",
)


def _data_url(image_path: str) -> str:

    path = Path(image_path)

    data = base64.b64encode(path.read_bytes()).decode("ascii")

    suffix = path.suffix.lower().lstrip(".") or "png"

    mime = "jpeg" if suffix in ("jpg", "jpeg") else suffix

    return f"data:image/{mime};base64,{data}"


def _openrouter_see(question: str, image_path: str) -> dict:

    key = (os.getenv("OPENROUTER_API_KEY") or "").strip()

    if not key:

        return {"success": False, "error": "OPENROUTER_API_KEY is not set."}

    models = list(
        getattr(settings, "OPENROUTER_VISION_MODELS", FALLBACK_MODELS) or FALLBACK_MODELS
    )

    client = OpenAI(api_key=key, base_url=OPENROUTER_URL, timeout=90)

    url = _data_url(image_path)

    last_error = ""

    for model in models:

        try:

            reply = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": question},
                            {"type": "image_url", "image_url": {"url": url}},
                        ],
                    }
                ],
                max_tokens=int(getattr(settings, "ZAI_VISION_MAX_TOKENS", 900)),
                temperature=0.3,
            )

            answer = (reply.choices[0].message.content or "").strip()

            if answer:

                return {
                    "success": True,
                    "provider": "openrouter",
                    "model": model,
                    "answer": answer,
                }

            last_error = f"{model} returned an empty answer."

        except Exception as error:

            last_error = f"{model}: {error}"

            logger.info("OpenRouter vision %s failed: %s", model, error)

    return {"success": False, "provider": "openrouter", "error": last_error}


def see(question: str, image_path: str) -> dict:
    """Ask about an image: z.ai first, then the free OpenRouter models."""

    first = ZaiProvider().see(question, image_path)

    if first.get("success"):

        return first

    first_error = str(first.get("error") or "The vision model did not answer.")

    logger.info("z.ai vision failed (%s); trying OpenRouter", first_error[:120])

    fallback = _openrouter_see(question, image_path)

    if fallback.get("success"):

        return fallback

    error = first_error

    if fallback.get("error"):

        error = f"{first_error} | {fallback['error']}"

    return {"success": False, "error": error}
