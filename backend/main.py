from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from brain.brain import Brain
from api.voice import router as voice_router

from config.logger import setup_logger

setup_logger()

app = FastAPI(
    title="JARVIS AI",
    version="1.0.0"
)

brain = Brain()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Voice API
app.include_router(voice_router)


@app.get("/")
def home():
    return {
        "assistant": "JARVIS",
        "status": "Running"
    }


@app.post("/chat")
def chat(data: dict):
    message = data.get("message", "")

    response = brain.chat(message)

    return response