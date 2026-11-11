import json
import platform
import socket
import subprocess
from pathlib import Path

import psutil
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from brain.brain import Brain
from api.voice import router as voice_router
from config.settings import settings

app = FastAPI(
    title="JARVIS AI",
    version="1.0.0"
)

brain = Brain()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Voice API
app.include_router(voice_router)

MEMORY_FILE = Path(__file__).parent / "data" / "memory.json"


def system_stats() -> dict:
    cpu = psutil.cpu_percent(interval=0.2)
    memory = psutil.virtual_memory()
    try:
        disk = psutil.disk_usage("C:\\")
    except OSError:
        disk = psutil.disk_usage("/")
    return {
        "cpu": round(cpu),
        "memory": round(memory.percent),
        "storage": round(disk.percent),
    }


@app.get("/")
def home():
    return {
        "assistant": "JARVIS",
        "status": "Running"
    }


@app.post("/chat")
def chat(data: dict):
    message = (data.get("message") or "").strip()

    if not message:
        raise HTTPException(status_code=400, detail="message is required")

    return brain.chat(message)


@app.get("/stats")
def stats():
    """Dashboard stats for the Mina frontend: {cpu, memory, storage}."""
    try:
        return system_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/system-info")
def get_system_info():
    try:
        info = system_stats()

        hostname = socket.gethostname()
        try:
            ip = socket.gethostbyname(hostname)
        except Exception:
            ip = "127.0.0.1"

        network = "Offline"
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            network = "Online"
        except Exception:
            pass

        return {
            "cpu": info["cpu"],
            "ram": info["memory"],
            "storage": info["storage"],
            "network": network,
            "os": platform.system(),
            "hostname": hostname,
            "ip": ip,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


LAUNCH_COMMANDS = {
    "chrome": [r"C:\Program Files\Google\Chrome\Application\chrome.exe"],
    "vscode": ["code"],
    "explorer": ["explorer"],
    "terminal": ["cmd", "/c", "start", "cmd"],
    "calculator": ["cmd", "/c", "start", "calc"],
    "settings": ["cmd", "/c", "start", "ms-settings:"],
}


def open_application(app_name: str) -> str:
    app_name = (app_name or "").lower().strip()
    if app_name not in LAUNCH_COMMANDS:
        raise HTTPException(status_code=404, detail=f"Unknown application: {app_name}")

    try:
        subprocess.Popen(LAUNCH_COMMANDS[app_name], shell=False)
    except FileNotFoundError:
        subprocess.Popen(LAUNCH_COMMANDS[app_name], shell=True)

    return f"Opening {app_name}."


@app.post("/launch")
def launch(data: dict):
    """Body: {app: "chrome"} -> {reply: "Opening chrome."}"""
    name = data.get("app", "")
    message = open_application(name)
    return {"reply": message, "success": True, "app": name}


@app.post("/open-app/{app_name}")
def open_app(app_name: str):
    try:
        message = open_application(app_name)
        return {"success": True, "message": message}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memory")
def get_memory():
    """Everything JARVIS remembers: profile, stored facts and free-form notes."""
    return {
        "success": True,
        "profile": brain.memory.get_profile(),
        "facts": brain.memory.all_facts(),
        "notes": brain.memory.notes(),
        "conversation_count": len(brain.memory.get_messages()),
    }


@app.post("/memory")
def add_memory(data: dict):
    text = (data.get("text") or data.get("note") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    result = brain.memory.add_note(text)

    return {
        "success": True,
        "reply": result.get("message", "Saved to memory."),
        "notes": brain.memory.notes(),
    }


@app.delete("/memory/note/{index}")
def delete_memory_note(index: int):
    result = brain.memory.delete_note(index)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message", "Note not found."))
    return {"success": True, "notes": result.get("notes", [])}


@app.delete("/memory/fact/{key}")
def delete_memory_fact(key: str):
    result = brain.memory.forget(key)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message", "Fact not found."))
    return {"success": True, "facts": brain.memory.all_facts()}


@app.post("/memory/clear")
def clear_memory(data: dict | None = None):
    scope = (data or {}).get("scope", "all")

    if scope == "conversation":
        brain.memory.clear_messages()
    else:
        brain.memory.clear()

    return {
        "success": True,
        "profile": brain.memory.get_profile(),
        "facts": brain.memory.all_facts(),
        "notes": brain.memory.notes(),
    }
