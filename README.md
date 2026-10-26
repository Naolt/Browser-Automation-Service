# Browser Automation Service

> Built at Fluid AI (2025), open-sourced with permission.

A FastAPI service that books restaurant tables by driving a real Chrome browser with an AI agent. You send a plain-language instruction ("book a table for 2 at 7pm tomorrow at …"), and a [browser-use](https://github.com/browser-use/browser-use) agent opens the restaurant on Google Maps, finds the best way to reserve (Google, OpenTable or SevenRooms), fills in the form and reports back.

## How it works

```
POST /api/v1/book ──▶ TaskService queue ──▶ worker 1..N ──CDP──▶ pre-launched Chrome profile 1..N
        │                    │                    │
        │                    ▼                    ▼
        │              Firestore (task       browser-use Agent (GPT-4o)
        │              status + result)      + custom reservation actions
        ▼
GET /api/v1/status/{id}, GET /api/v1/result/{id}
```

- **Workers and Chrome profiles**: each worker connects over the Chrome DevTools Protocol to its own Chrome instance, started from a profile that is already signed in to Google. This avoids login and verification prompts during bookings.
- **Self-healing**: `TaskService` checks its browser agents and restarts any that crash or lose their CDP connection.
- **Custom actions** (`services/actions`): the agent's browser-use `Controller` is extended with reservation-specific actions, such as finding reservation options on a Google Maps page, choosing the best provider, preparing tabs and updating contact details.
- **Providers** (`services/actions/provider`): Google, OpenTable and SevenRooms each implement `BaseReservationProvider`. `ReservationDiscoveryService` collects every option on the page and picks the best one.
- **Persistence**: task status and results are stored in Firestore.

## Tech stack

Python · FastAPI · browser-use · LangChain (OpenAI GPT-4o) · Chrome DevTools Protocol · Firebase / Firestore · Pydantic

## Running it

Requires Python 3.11+, Google Chrome, an OpenAI API key and a Firebase project with Firestore enabled.

```bash
git clone https://github.com/Naolt/Browser-Automation-Service.git
cd Browser-Automation-Service
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # set FIREBASE_* values, and add OPENAI_API_KEY
```

1. Download a Firebase service account key and point `FIREBASE_SERVICE_ACCOUNT_PATH` at it.
2. Create the Chrome profiles and sign in to Google once in each window:
   ```bash
   python create_profiles.py
   ```
3. Launch the profiles with remote debugging enabled:
   ```bash
   python launch_chrome_profiles.py
   ```
4. Start the API on port 8000:
   ```bash
   python main.py
   ```

Book a table:

```bash
curl -X POST http://localhost:8000/api/v1/book \
  -H "Content-Type: application/json" \
  -d '{"task": "Book a table for 2 at 7pm tomorrow at <restaurant name>, <city>. Name: Jane Doe, phone: +1 555 0100, email: jane@example.com"}'
# → {"session_id": "..."}

curl http://localhost:8000/api/v1/status/<session_id>
curl http://localhost:8000/api/v1/result/<session_id>
```

## API

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/book` | Queue a booking task; returns `session_id` |
| GET | `/api/v1/status/{session_id}` | Task status |
| GET | `/api/v1/result/{session_id}` | Final result or error |
| WS | `/api/v1/ws/{task_id}` | WebSocket subscription (connection handling only; updates not yet sent) |

## Project structure

```
main.py                     # FastAPI app, starts and stops the worker pool
config.py                   # settings from .env
create_profiles.py          # create and sign in to Chrome profiles
launch_chrome_profiles.py   # launch profiles with CDP ports
routes/task_routes.py       # REST + WebSocket endpoints
models/                     # task and reservation models
services/
├── task_service.py         # queue, workers, health checks and restarts
├── browser_agent.py        # browser-use agent bound to one Chrome instance
├── firestore_service.py    # task persistence
├── websocket_manager.py    # WebSocket connection registry
├── reservation_*.py        # discovery and booking flow
└── actions/                # custom agent actions and providers
test/                       # scenario runners, test cases and evaluation
```
