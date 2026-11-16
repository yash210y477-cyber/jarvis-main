# JARVIS

A local desktop AI assistant: a React UI (the Mina app in
`jarvis-mina-home main/mina`) and a Python (FastAPI) core that owns everything
privileged.

```
React UI (Vite)  ──HTTP/WebSocket──▶  FastAPI core  ──▶  AI providers
      │                                   ├── SQLite memory
                                          ├── Windows launcher
                                          └── system monitor / voice
```

The backend is the single source of truth. The UI only displays state;
launching apps and reading system information happen in Python.

## Requirements

- Windows (application launching and voice are Windows-specific)
- Python 3.11+
- Node.js 22+

## Backend setup

```bash
cd backend

python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt

# Optional: microphone, Whisper STT, TTS
venv\Scripts\python.exe -m pip install -r requirements-voice.txt

copy .env.example .env
# Edit .env and add the provider keys you have.
# At least one provider key is required for general chat.
```

Run it:

```bash
venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload --reload-exclude "data" --reload-exclude ".venv" --reload-exclude "*.log" --reload-exclude "*.session" --reload-exclude "*.db*"
```

Only a `.py` change restarts the server, but the reloader still watches every file
under the working folder — including the 49,000 files in `.venv` and the bundled
runtime in `data/tools`. The excludes keep it to the code that matters.

The API is then at <http://127.0.0.1:8000> and its docs at `/docs`.

## Frontend setup

```bash
cd "jarvis-mina-home main/mina"
npm install
npm run dev          # http://127.0.0.1:5173
npm run build        # production bundle in dist
```

If the API lives somewhere else, set `VITE_API_URL` before building or
running Vite.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/` | Health and version |
| POST | `/chat` | `{ "message": "...", "mode": "assistant" }` |
| GET | `/system-info` | Cached CPU / RAM / storage / network / battery |
| POST | `/open-app/{name}` | Launch an installed app |
| POST | `/close-app/{name}` | Ask an app to close (graceful, no force) |
| GET | `/capabilities` | Modes, providers, apps, intents, voice |
| GET | `/models` | Provider availability and active mode |
| GET | `/memory` | Profile, facts, message count, summary |
| POST | `/memory/clear` | `{ "scope": "conversation" }` or `"all"` |
| POST | `/voice` | One microphone turn |
| POST | `/voice/live` | Start continuous listening |
| POST | `/voice/stop` | Stop listening |
| GET | `/voice/status` | `{ running, available }` |
| WS | `/ws/voice` | Live `listening` / `heard` / `reply` / `stopped` events |

Prompt modes: `assistant`, `coding`, `teacher`, `research`.

## Memory

Memory lives in `backend/data/jarvis.db` (SQLite, WAL mode, one shared locked
connection). On first start an existing `backend/data/memory.json` is imported
once and left in place.

When a conversation reaches 50 messages the core generates a rolling summary
and keeps the 10 most recent messages. If no provider is available the raw
messages are kept instead of being discarded.

## Security

- `backend/.env` is no longer tracked by git; only `.env.example` is.
- CORS allows only the local UI origins.
- Every state-changing request (`POST`/`PUT`/`PATCH`/`DELETE`) must come from
  an allowed local `Origin`; `Sec-Fetch-Site: cross-site` is rejected.
- Set `JARVIS_LOCAL_TOKEN` in `backend/.env` to additionally require an
  `X-Jarvis-Token` header on state-changing requests.
- Provider keys never leave the backend.

### Required manual actions

1. **Rotate the provider keys** that were previously committed to
   `backend/.env`. Use each provider's dashboard, then update `.env`.
2. **Purge the old blob from git history.** Rewriting history is destructive
   and needs a force-push, so it is intentionally not automated:

   ```bash
   # with git-filter-repo installed
   git filter-repo --path backend/.env --invert-paths
   git push --force-with-lease
   ```

   Rotating the keys is mandatory; purging history only removes the old values
   from clones. Coordinate with anyone else who has the repository.

## Tests and CI

```bash
cd backend
venv\Scripts\python.exe -m pytest        # memory, intent, API, voice guard
```

`.github/workflows/ci.yml` runs the backend suite (without the heavy voice
dependencies).

## Known limitations

- Replies are not streamed token-by-token; the UI shows a typing indicator and
  renders the complete Markdown answer.
- Voice requires the optional dependencies and a working microphone. Without
  them the API reports voice as unavailable instead of crashing.
- No user accounts: the API binds to loopback and trusts the local machine.
