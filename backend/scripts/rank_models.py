"""Measure every free model we can reach and write the ranking used in chat.

Each model gets three small checks with known answers (so quality is a number,
not a feeling) and the time each answer took. The result goes to
``data/model_ranking.json``; the providers and the manager read it to decide who
answers first. Run it again whenever models change:

    ./.venv/Scripts/python.exe scripts/rank_models.py
"""

import concurrent.futures
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import find_dotenv, load_dotenv  # noqa: E402

load_dotenv(find_dotenv(), override=True)

from openai import OpenAI  # noqa: E402

from memory.storage import data_dir  # noqa: E402

OUT = data_dir() / "model_ranking.json"

TIMEOUT = 60

CHECKS = (
    ("What is 17 multiplied by 23? Reply with the number only.", ("391",)),
    ("Reply with exactly this word and nothing else: PONG", ("pong",)),
    ("Which city is the capital of Japan? One word.", ("tokyo",)),
    (
        "Write BANANA in capitals, then a hyphen, then the number 42. "
        "Reply with that only.",
        ("banana-42", "banana - 42"),
    ),
    (
        "A train covers 60 km in 40 minutes. How fast is that in km/h? "
        "Reply with the number only.",
        ("90",),
    ),
    # JARVIS is talked to in Hinglish, so it must answer in it.
    (
        "Ek line me Hinglish me batao ki aap kaise ho.",
        ("hai", "hoon", "kaise", "theek"),
    ),
)

# Free chat models we can reach with the keys on this machine.
TEXT = (
    ("groq", "https://api.groq.com/openai/v1", "GROQ_API_KEY", [
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "openai/gpt-oss-safeguard-20b",
        "qwen/qwen3.8-27b",
        "allam-2-7b",
    ]),
    ("openrouter", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", [
        "openrouter/free",
        "google/gemma-4-31b-it:free",
        "google/gemma-4-26b-a4b-it:free",
        "nvidia/nemotron-3.5-lightning:free",
        "nvidia/nemotron-3-ultra-550b-a55b:free",
        "cohere/north-mini-code:free",
        "baidu/ernie-5.5-flash-preview:free",
        "inclusionai/ling-3.2-flash:free",
        "liquid/lfm-3-1.7b:free",
        "recursive/flint-v1.0:free",
        "dots-studio/dots-3-note-preview:free",
    ]),
    ("zai", "https://api.z.ai/api/paas/v4/", "ZAI_API_KEY", [
        "glm-4.7-flash",
        "glm-4.5-flash",
    ]),
)

VISION = (
    ("zai", "https://api.z.ai/api/paas/v4/", "ZAI_API_KEY", ["glm-4.6v-flash"]),
    ("openrouter", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", [
        "inclusionai/ling-3.2-flash:free",
        "nvidia/nemotron-3.5-super-vl:free",
        "particle-ai/particle-1:free",
        "google/gemma-4-31b-it:free",
        "dots-studio/dots-3-note-preview:free",
        "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
    ]),
)

OLLAMA = ("qwen2.5:3b", "llama3.2:latest")


def clients():
    made = {}

    for name, base, key, _models in TEXT + VISION:
        if name in made:
            continue
        secret = (os.getenv(key) or "").strip()
        if secret:
            made[name] = OpenAI(api_key=secret, base_url=base, timeout=TIMEOUT)

    if os.getenv("OLLAMA_HOST"):
        made["ollama"] = OpenAI(
            api_key="ollama", base_url="http://127.0.0.1:11434/v1", timeout=TIMEOUT
        )
    else:
        made["ollama"] = OpenAI(
            api_key="ollama", base_url="http://127.0.0.1:11434/v1", timeout=TIMEOUT
        )

    return made


def picture_question():
    """A white card with a red square, as a data URL, with the question."""

    import base64
    import io

    from PIL import Image, ImageDraw

    image = Image.new("RGB", (240, 160), "white")
    ImageDraw.Draw(image).rectangle([40, 40, 200, 120], fill="red")

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")

    return (
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "What colour is the square? One word."},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{encoded}"},
                },
            ],
        },
        ("red",),
    )


def score_model(client, model, vision=False):
    """Ask the checks; return quality, total time, and any error."""

    quality = 0
    took = 0.0
    error = ""

    checks = [picture_question()] if vision else list(CHECKS)

    for check in checks:

        if vision:

            message, expected = check
            messages = [message]
            limit = 300

        else:

            prompt, expected = check
            messages = [{"role": "user", "content": prompt}]
            limit = 600

        started = time.time()
        reply = None

        # A busy free endpoint is worth one more try before calling it broken.
        for attempt in (1, 2, 3):

            try:
                reply = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=limit,
                    temperature=0,
                )
                break

            except Exception as failure:

                error = f"{type(failure).__name__}: {failure}"[:200]

                if attempt < 3 and any(
                    word in error.lower()
                    for word in ("429", "1305", "overload", "rate limit")
                ):
                    time.sleep(3 * attempt)
                    continue

                break

        if reply is None:
            break

        took += time.time() - started

        text = (reply.choices[0].message.content or "").lower()

        if any(word in text for word in expected):
            quality += 1

        # The user talks in English/Hinglish, so an answer written in another
        # script is a miss even when the fact in it is right.
        if re.search(r"[^\x00-\x7F]", text):
            quality = max(0, quality - 1)

        error = ""

    return quality, round(took, 2), error


def rank(entries):
    """Best first: more correct answers, then less time."""

    ok = [item for item in entries if not item["error"]]
    ok.sort(key=lambda item: (-item["quality"], item["seconds"]))
    broken = [item for item in entries if item["error"]]
    return ok + broken


def main():
    only = [name.strip().lower() for name in sys.argv[1:] if not name.startswith("-")]

    made = clients()
    jobs = []

    for name, _base, _key, models in TEXT:
        if name in made and (not only or name in only):
            jobs += [(name, model) for model in models]

    for name, _base, _key, models in VISION:
        if name in made and (not only or name in only):
            jobs += [(name, f"vision::{entry}") for entry in models]

    if not only or "ollama" in only:
        jobs += [("ollama", model) for model in OLLAMA]

    def work(job):
        name, model = job
        vision = model.startswith("vision::")
        real = model.split("::", 1)[1] if vision else model
        quality, seconds, error = score_model(made[name], real, vision=vision)
        result = {
            "provider": name,
            "model": real,
            "role": "vision" if vision else "text",
            "quality": quality,
            "of": 1 if vision else len(CHECKS),
            "seconds": seconds,
            "error": error,
        }
        print(
            f"{name:11} {real:45} quality={quality}/{1 if vision else len(CHECKS)} "
            f"{seconds:6.1f}s {('ERR ' + error[:60]) if error else ''}",
            flush=True,
        )
        return result

    # Free tiers rate-limit quickly, so the models are measured a few at a time.
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        entries = list(pool.map(work, jobs))

    # A partial run keeps the rows it did not measure.
    if only and OUT.exists():

        try:
            old = json.loads(OUT.read_text(encoding="utf-8"))

        except (OSError, ValueError):
            old = {}

        fresh = {(item["provider"], item["model"]) for item in entries}

        entries += [
            row
            for row in (old.get("text") or []) + (old.get("vision") or [])
            if (row["provider"], row["model"]) not in fresh
        ]

    text = rank([e for e in entries if e["role"] == "text"])
    see = rank([e for e in entries if e["role"] == "vision"])

    OUT.write_text(
        json.dumps({"text": text, "vision": see, "measured": time.time()}, indent=2),
        encoding="utf-8",
    )

    print("\nTEXT BEST FIRST:")
    for item in text:
        mark = "ERR" if item["error"] else f"{item['quality']}/{item['of']}"
        print(f"  {mark:5} {item['seconds']:6.1f}s {item['provider']} / {item['model']}")

    print("\nVISION BEST FIRST:")
    for item in see:
        mark = "ERR" if item["error"] else f"{item['quality']}/{item['of']}"
        print(f"  {mark:5} {item['seconds']:6.1f}s {item['provider']} / {item['model']}")

    print(f"\nwritten to {OUT}")


if __name__ == "__main__":
    main()
