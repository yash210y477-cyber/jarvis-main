import platform
import socket
import subprocess
from pathlib import Path

import psutil
from fastapi import (
    FastAPI,
    HTTPException,
    Security,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from brain.brain import Brain
from api.voice import router as voice_router
from config.security import check_request
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


@app.middleware("http")
async def origin_guard(request, call_next):
    """Reject state-changing calls from foreign origins."""

    error = check_request(request.method, request.headers)

    if error:

        return JSONResponse(
            status_code=403,
            content={"success": False, "error": error},
        )

    return await call_next(request)


# Voice API
app.include_router(voice_router)

MEMORY_FILE = Path(__file__).parent / "data" / "memory.json"

MODES = ["assistant", "coder", "researcher", "friend"]

INTENTS = [
    "open_app",
    "close_app",
    "search_web",
    "open_website",
    "system_status",
    "remember",
    "recall",
]


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


def network_state() -> str:

    try:

        socket.create_connection(("8.8.8.8", 53), timeout=2)

        return "Online"

    except Exception:

        return "Offline"


@app.get("/")
def home():
    return {
        "assistant": "JARVIS",
        "status": "Running"
    }


@app.get("/capabilities")
def capabilities():
    """What this build can do, for the UI to advertise."""

    return {
        "success": True,
        "assistant": "JARVIS",
        "version": settings.APP_VERSION,
        "modes": MODES,
        "intents": INTENTS,
        "voice": {
            "websocket": "/ws/voice",
            "record_endpoint": "/voice",
            "stt": True,
            "tts": True,
        },
        "tools": [tool["name"] for tool in brain.registry.metadata()],
        "memory": {
            "profile": True,
            "facts": True,
            "notes": True,
        },
    }


@app.get("/memory/search")
def memory_search(q: str = "", limit: int = 3):
    """Search everything JARVIS remembers by meaning, not exact words."""

    from memory.semantic import get_semantic

    semantic = get_semantic()

    semantic.sync()

    results = semantic.search(q, limit=limit)

    return {"success": True, "query": q, "results": results, **semantic.stats()}

@app.post("/documents/index")
def documents_index(data: dict = None):
    """Extract and index real folders so files can be found by meaning."""

    from memory.documents import index_documents

    payload = data or {}

    folders = payload.get("folders")

    if isinstance(folders, str):

        folders = [folders]

    return index_documents(folders, int(payload.get("limit") or 200))


@app.get("/documents/status")
def documents_status():

    from memory.documents import status

    return status()


@app.get("/models")
def models():
    """Configured providers and whether they can answer right now."""

    providers = []

    for provider in brain.ai.providers:

        try:

            available = bool(provider.health())

        except Exception:

            available = False

        model = getattr(provider, "model", None)

        if isinstance(model, dict):

            model = model.get("model_name") or model.get("name")

        providers.append({
            "name": provider.name(),
            "model": model,
            "available": available,
        })

    return {
        "success": True,
        "providers": providers,
        "any_available": any(item["available"] for item in providers),
    }


@app.post("/chat")
def chat(data: dict):
    message = (data.get("message") or "").strip()

    if not message:
        raise HTTPException(status_code=400, detail="message is required")

    return brain.chat(message, model=data.get("model"))


@app.get("/stats")
def stats():
    """Dashboard stats for the Mina frontend: {cpu, memory, storage}."""
    try:
        return system_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/images/{name}")
def get_image(name: str):
    """A generated picture, for the chat to show instead of opening a folder."""

    from tools import image_gen

    path = image_gen.images_dir() / Path(name).name

    if not path.is_file():
        raise HTTPException(status_code=404, detail="No such image")

    return FileResponse(path, media_type="image/png", filename=path.name)


@app.post("/images/{name}/download")
def download_image(name: str):
    """Copy a generated picture into Downloads/Jarvis, on request."""

    from tools import image_gen

    return image_gen.save_to_downloads(name)


@app.get("/system-info")
def get_system_info():
    try:
        hostname = socket.gethostname()

        try:
            ip = socket.gethostbyname(hostname)
        except Exception:
            ip = "127.0.0.1"

        info = system_stats()

        return {
            "success": True,
            "cpu": int(info["cpu"]),
            "ram": int(info["memory"]),
            "storage": int(info["storage"]),
            "network": network_state(),
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


def _chat_when(stamp) -> str:
    """A chat's date in a form a person reads."""

    from datetime import datetime

    try:

        moment = datetime.fromtimestamp(float(stamp or 0))

    except (ValueError, OSError, OverflowError):

        return ""

    return moment.strftime("%d %b %Y, %I:%M %p").replace(" 0", " ")


@app.get("/chats")
def chats(limit: int = 60):
    """Past conversations, newest first, each with its date."""

    items = brain.memory.chats(limit)

    for item in items:

        item["date"] = _chat_when(item.get("started_at"))
        item["updated"] = _chat_when(item.get("updated_at"))

    return {"success": True, "chats": items, "count": len(items)}


@app.get("/chats/{chat_id}")
def chat_detail(chat_id: int):

    messages = brain.memory.chat_messages(chat_id)

    for message in messages:

        message["time"] = _chat_when(message.get("at"))

    return {"success": True, "id": chat_id, "messages": messages}


@app.post("/chats/new")
def chat_new(data: dict | None = None):

    title = ((data or {}).get("title") or "").strip()

    chat_id = brain.memory.start_chat(title)

    return {"success": True, "id": chat_id, "date": _chat_when(__import__("time").time())}


@app.delete("/chats/{chat_id}")
def chat_delete(chat_id: int):

    removed = brain.memory.delete_chat(chat_id)

    return {"success": removed, "id": chat_id}


@app.get("/tools")
def list_tools():
    """Tool catalogue the agent can call, with schemas and permissions."""
    return {
        "success": True,
        "tools": brain.registry.metadata(),
        "count": len(brain.registry.all()),
    }


@app.websocket("/ws/voice")
async def voice_socket(websocket: WebSocket):
    """Streaming voice channel: text in, JARVIS reply out."""

    await websocket.accept()

    origin = (websocket.headers.get("origin") or "").rstrip("/")

    if origin and origin not in settings.ALLOWED_ORIGINS:

        await websocket.close(code=1008)

        return

    await websocket.send_json({"status": "ready"})

    try:

        while True:

            message = await websocket.receive_text()

            if not message.strip():

                continue

            reply = brain.chat(message)

            await websocket.send_json({"heard": message, **reply})

    except WebSocketDisconnect:

        return


# -----------------------------
# Proactive + remote
# -----------------------------


@app.on_event("startup")
def start_services():
    from memory.semantic import warm_up_async
    from reminders.scheduler import SCHEDULER
    from remote.telegram import BRIDGE

    SCHEDULER.start(
        memory=brain.memory,
        briefing_hour=settings.MORNING_BRIEFING_HOUR,
        briefing_minute=settings.MORNING_BRIEFING_MINUTE,
    )

    BRIDGE.start(brain)

    # Load the embedding model off the request path.
    try:

        warm_up_async()

    except Exception:

        pass

    try:

        from remote.telegram_calls import CALL_BRIDGE

        CALL_BRIDGE.attach_brain(brain)

        CALL_BRIDGE.start()

    except Exception:

        pass

    # Push-to-talk: hold Ctrl+Alt anywhere and speak.
    if settings.COMPANION_AUTOSTART:

        try:

            from api.voice import voice as voice_engine
            from tools import companion

            companion.configure(handler=brain.chat, speaker=voice_engine)
            companion.start()

        except Exception:

            pass


@app.on_event("shutdown")
def stop_services():
    from reminders.scheduler import SCHEDULER
    from remote.telegram import BRIDGE

    SCHEDULER.stop()
    BRIDGE.stop()

    try:

        from remote.telegram_calls import CALL_BRIDGE

        CALL_BRIDGE.stop()

    except Exception:

        pass

    try:

        from tools import companion

        companion.stop()

    except Exception:

        pass

    # A reply still waiting on a provider must not keep Ctrl+C hanging.
    from brain.brain import shutdown_pool

    shutdown_pool()


@app.post("/companion/start")
def companion_start():

    from tools import companion

    companion.configure(handler=brain.chat, speaker=_voice_engine())

    return companion.start()


@app.post("/companion/stop")
def companion_stop():

    from tools import companion

    return companion.stop()


@app.get("/companion/status")
def companion_status():

    from tools import companion

    return companion.status()


@app.get("/companion/events")
def companion_events():

    from tools import companion

    return companion.events()


@app.post("/screen/area")
def screen_area_ask(data: dict = None):

    from tools import screen_area

    question = ((data or {}).get("question") or "").strip()

    return screen_area.ask_area(question)


@app.post("/card/show")
def card_show(data: dict):

    from tools import card

    text = (data.get("text") or "").strip()

    if not text:

        raise HTTPException(status_code=400, detail="text is required")

    return card.show_card(
        title=data.get("title") or "JARVIS",
        text=text,
        seconds=int(data.get("seconds") or 25),
    )


def _voice_engine():

    try:

        from api.voice import voice as engine

        return engine

    except Exception:

        return None


@app.get("/reminders")
def get_reminders():
    from reminders.scheduler import SCHEDULER

    return {
        "success": True,
        "reminders": SCHEDULER.list(),
        "status": SCHEDULER.status(),
    }


@app.post("/reminders")
def create_reminder(data: dict):
    from reminders.scheduler import SCHEDULER

    text = (data.get("text") or "").strip() or "reminder"
    result = SCHEDULER.add(text, data.get("when") or "", data.get("seconds"))

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result


@app.delete("/reminders/{reminder_id}")
def delete_reminder(reminder_id: str):
    from reminders.scheduler import SCHEDULER

    result = SCHEDULER.cancel(reminder_id)

    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))

    return result


@app.delete("/reminders")
def clear_reminders():
    from reminders.scheduler import SCHEDULER

    return SCHEDULER.clear()


@app.get("/briefing")
def briefing():
    from reminders.scheduler import SCHEDULER

    return {
        "success": True,
        "briefing": SCHEDULER.briefing(),
    }


@app.post("/notify")
def send_notification(data: dict):
    from notify.toast import notify

    return notify(
        data.get("title") or "JARVIS",
        data.get("message") or "",
        data.get("app") or "JARVIS",
    )


@app.post("/screen/watch/start")
def screen_watch_start():
    from tools import screen_watch

    return screen_watch.start()


@app.post("/screen/watch/stop")
def screen_watch_stop():
    from tools import screen_watch

    return screen_watch.stop()


@app.get("/screen/watch/status")
def screen_watch_status():
    from tools import screen_watch

    return screen_watch.status()


@app.get("/screen/watch/events")
def screen_watch_events(since: int = 0):
    from tools import screen_watch

    return {"success": True, "events": screen_watch.events(since)}


@app.get("/telegram/status")
def telegram_status():
    from remote.telegram import BRIDGE

    return BRIDGE.status()


# -----------------------------
# Telegram voice calls (user account)
# -----------------------------


@app.get("/telegram-call/status")
def telegram_call_status():

    from remote.telegram_calls import CALL_BRIDGE

    return CALL_BRIDGE.status()


@app.post("/telegram-call/login/start")
async def telegram_call_login_start(data: dict):

    from remote.telegram_user import start_login

    phone = (data.get("phone") or "").strip()

    if not phone:

        raise HTTPException(status_code=400, detail="phone is required")

    return await start_login(phone)


@app.post("/telegram-call/login/verify")
async def telegram_call_login_verify(data: dict):

    from remote.telegram_user import verify_login

    code = str(data.get("code") or "").strip()

    if not code:

        raise HTTPException(status_code=400, detail="code is required")

    return await verify_login(code, (data.get("password") or "").strip())


@app.post("/telegram-call/start")
def telegram_call_start():

    from remote.telegram_calls import CALL_BRIDGE

    return CALL_BRIDGE.start()


@app.post("/telegram-call/stop")
def telegram_call_stop():

    from remote.telegram_calls import CALL_BRIDGE

    return CALL_BRIDGE.stop()


@app.post("/telegram-call/answer")
def telegram_call_answer(data: dict):

    from remote.telegram_calls import CALL_BRIDGE

    chat_id = data.get("chat_id")

    if chat_id is None:

        raise HTTPException(status_code=400, detail="chat_id is required")

    return CALL_BRIDGE.answer(chat_id, int(data.get("seconds") or 0))


@app.post("/telegram-call/say")
def telegram_call_say(data: dict):

    from remote.telegram_calls import CALL_BRIDGE

    text = (data.get("text") or "").strip()

    if not text:

        raise HTTPException(status_code=400, detail="text is required")

    return CALL_BRIDGE.say(text, data.get("chat_id"))


@app.post("/telegram-call/hangup")
def telegram_call_hangup(data: dict):

    from remote.telegram_calls import CALL_BRIDGE

    chat_id = data.get("chat_id")

    if chat_id is None:

        raise HTTPException(status_code=400, detail="chat_id is required")

    return CALL_BRIDGE.hangup(chat_id)
