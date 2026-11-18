# JARVIS

A local desktop AI assistant. A React/Vite UI talks to a FastAPI core that owns
everything privileged: AI providers, tools, memory, voice, messaging and the
Windows desktop.

```
React UI (Vite)  ──HTTP/WebSocket──▶  FastAPI core  ──▶  AI providers
      │                                   ├── SQLite memory
                                          ├── tools (apps, files, mail, calendar, …)
                                          └── system monitor / voice
```

The backend is the single source of truth. The UI only displays state; launching
apps, reading files and controlling the system happen in Python.

## What it does

- **Chat** with a fallback chain across free and paid providers (Groq, Z.ai,
  OpenRouter, Ollama, Anthropic) plus offline local intents that need no model.
- **54 tools**: open/close apps, files, screenshots, screen reading and typing,
  browser tabs, WhatsApp/Telegram messaging, reminders, email (SMTP/IMAP),
  calendar (`.ics` files), image generation, volume/media, clipboard, shell.
- **Memory**: SQLite conversation store, profile/facts/notes, semantic search
  with a local embedding model, folder/document indexing.
- **Voice**: Whisper speech-to-text, SAPI/Edge text-to-speech, push-to-talk
  companion, Telegram voice calls.
- **Approvals**: tools that change the machine ask first; the chat shows an
  ALLOW/CANCEL card.

## Layout

```
backend/        FastAPI app, providers, tools, memory, voice, tests
frontend/mina/  React + TypeScript + Vite + Tailwind chat UI
.github/        CI workflow (backend test suite)
```

## Requirements

- Windows 10/11 for the desktop, voice and Windows-specific tools
  (the backend still starts on Linux/macOS, minus those features)
- Python 3.11+
- Node.js 18+ (22 recommended)

## Setup

### Backend

```bat
cd backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
```

Then edit `backend\.env` and add at least one provider key (see
[Environment variables](#environment-variables)).

Optional extras:

```bat
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt    :: pytest + httpx
.venv\Scripts\python.exe -m pip install -r requirements-voice.txt  :: voice pipeline
```

### Frontend

```bat
cd frontend\mina
npm install
copy .env.example .env
```

The frontend `.env` is optional: without it the UI calls
`http://127.0.0.1:8080` and sends no token.

## Run

Backend (terminal 1):

```bat
cd backend
.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8080
```

Frontend (terminal 2):

```bat
cd frontend\mina
npm run dev
```

Open <http://127.0.0.1:5173>. API docs: <http://127.0.0.1:8080/docs>.

Production frontend build:

```bat
cd frontend\mina
npm run build      :: output in dist/
```

## Environment variables

Backend variables live in `backend\.env` (start from `backend\.env.example`).
Only the provider keys are needed for general chat; every feature degrades with a
friendly message when its settings are missing.

| Variable | Purpose |
| --- | --- |
| `GROQ_API_KEY`, `GROQ_MODEL`, `GROQ_FALLBACK_MODEL` | Groq provider |
| `GROQ_STT`, `GROQ_STT_MODEL`, `GROQ_STT_TIMEOUT` | Phone calls transcribe on Groq Whisper (~0.5s), local model as fallback |
| `OPENROUTER_API_KEY` | OpenRouter provider and image generation |
| `ZAI_API_KEY`, `ZAI_MODEL` | Z.ai / Zhipu GLM provider |
| `SILICONFLOW_API_KEY`, `SILICONFLOW_MODEL` | SiliconFlow provider |
| `ANTHROPIC_API_KEY` | Final Claude fallback |
| `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `ENABLE_OLLAMA` | Local model, no API key |
| `JARVIS_LOCAL_TOKEN` | Require `X-Jarvis-Token` on state-changing requests |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_SSL` | Sending email |
| `IMAP_HOST`, `IMAP_PORT` | Reading the inbox (uses `SMTP_USER`/`SMTP_PASSWORD`) |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_CHAT_IDS` | Telegram bridge |
| `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_CALL_*` | Telegram voice calls |
| `JARVIS_BRIEFING_HOUR`, `JARVIS_BRIEFING_MINUTE` | Morning briefing time |
| `JARVIS_NOTIFICATIONS`, `JARVIS_LANGUAGE` | Toast notifications, reply language |
| `SEMANTIC_MEMORY`, `SEMANTIC_MODEL`, `SEMANTIC_TOP_K`, `SEMANTIC_MIN_SCORE` | Semantic memory |
| `TTS_ENGINE`, `TTS_SAPI_VOICE`, `TTS_VOICE` | Text-to-speech voice |
| `IMAGE_MODEL` | Image generation model |
| `SCREEN_WATCH_INTERVAL`, `SCREEN_WATCH_COOLDOWN`, `SCREEN_WATCH_SPEAK` | Screen watching |
| `JARVIS_TOOLS_DIR` | Where bundled tool runtimes are stored |

Frontend variables live in `frontend\mina\.env`:

| Variable | Purpose |
| --- | --- |
| `VITE_API_URL` | Backend origin (default `http://127.0.0.1:8080`) |
| `VITE_JARVIS_TOKEN` | Must match `JARVIS_LOCAL_TOKEN`; empty when unused |

## Tests

```bat
cd backend
.venv\Scripts\python.exe -m pytest
```

`.github/workflows/ci.yml` runs the same suite on Ubuntu for every push.

## Security

- `backend/.env` and `frontend/mina/.env` are not tracked and are not part of
  this archive; only `.env.example` files are.
- CORS allows local UI origins only, and cross-site state-changing requests are
  rejected.
- Provider keys never leave the backend.
- Set `JARVIS_LOCAL_TOKEN` if other local processes should not be able to drive
  the assistant.

## Known limitations

- Replies are not streamed token-by-token; the UI shows a typing indicator.
- Voice needs the optional dependencies and a working microphone; without them
  the API reports voice as unavailable instead of crashing.
- No user accounts: the API binds to loopback and trusts the local machine.
- Desktop automation (app launching, window control, TTS) is Windows-only.
