from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from brain.brain import Brain

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


@app.get("/")
def home():

    return {
        "assistant": "JARVIS",
        "status": "Running"
    }


@app.post("/chat")
def chat(data: dict):

    message = data.get("message", "")

    response = brain.process(message)

    return response