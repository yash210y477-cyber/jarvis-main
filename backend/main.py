from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from brain.brain import Brain
from api.voice import router as voice_router
from config.logger import setup_logger

import psutil
import platform
import socket
import subprocess

setup_logger()

app = FastAPI(
    title="JARVIS AI",
    version="1.0.0"
)

brain = Brain()

# ----------------------------
# CORS
# ----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------
# Voice API
# ----------------------------
app.include_router(voice_router)


# ----------------------------
# Home
# ----------------------------
@app.get("/")
def home():
    return {
        "assistant": "JARVIS",
        "status": "Running"
    }


# ----------------------------
# Chat
# ----------------------------
@app.post("/chat")
def chat(data: dict):
    message = data.get("message", "")
    return brain.chat(message)


# ----------------------------
# System Information
# ----------------------------
@app.get("/system-info")
def get_system_info():
    try:
        cpu = psutil.cpu_percent(interval=0.5)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("C:\\")

        hostname = socket.gethostname()

        try:
            ip = socket.gethostbyname(hostname)
        except Exception:
            ip = "127.0.0.1"

        network = "Offline"

        try:
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            network = "Online"
        except:
            pass

        return {
            "cpu": round(cpu),
            "ram": round(memory.percent),
            "storage": round(disk.percent),
            "network": network,
            "os": platform.system(),
            "hostname": hostname,
            "ip": ip
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# ----------------------------
# Open Applications
# ----------------------------
@app.post("/open-app/{app_name}")
def open_app(app_name: str):
    try:

        app_name = app_name.lower()

        if app_name == "chrome":
            subprocess.Popen([
                r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            ])

        elif app_name == "vscode":
            subprocess.Popen(["code"])

        elif app_name == "explorer":
            subprocess.Popen(["explorer"])

        elif app_name == "terminal":
            subprocess.Popen("start cmd", shell=True)

        else:
            raise HTTPException(
                status_code=404,
                detail="Unknown application"
            )

        return {
            "success": True,
            "message": f"{app_name} opened"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )