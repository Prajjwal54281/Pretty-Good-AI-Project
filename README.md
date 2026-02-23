# PGA Voice Bot — Athena AI Agent Tester

Made By - Prajjwal Mishra

#Loom Video - loom.com/share/e23f735cbd21491086e80f269d068b5a

An automated voice bot that calls the Athena AI medical office agent (+1-805-439-8008), simulates realistic patient conversations, records full transcripts, and automatically detects bugs in the agent's responses.

## Architecture

The system is built around Vapi AI as the voice orchestration layer. When a test is triggered, the FastAPI backend sends a single API call to Vapi with a scenario-specific system prompt, persona, and opening line. Vapi creates an outbound phone call, handles telephony, speech-to-text, LLM dialogue (GPT-4o-mini), and text-to-speech — running the entire patient conversation autonomously. When the call ends, a background poller fetches the complete transcript from Vapi's API, runs nine regex-based bug detection patterns against the transcript (hold loops, missing ticket numbers, weekend bookings, failed escalations, record lookup failures, excessive identity verification, missing triage, and more), and persists everything to MongoDB. The React dashboard pulls from the backend API to display call history, full two-sided transcripts, and a bug report tracker with severity levels.

Vapi was chosen because it abstracts the entire voice stack into one API — no need to separately wire up Twilio for telephony, a transcription service, and a TTS engine. One POST request creates a complete phone call with an AI agent. The transient assistant pattern (a fresh assistant per call, configured inline) means each scenario gets its own system prompt and persona without needing to manage persistent assistants on Vapi's dashboard.

## Tech Stack

- **Backend**: Python / FastAPI
- **Frontend**: React / Tailwind CSS / shadcn/ui
- **Database**: MongoDB
- **Voice Pipeline**: Vapi AI (telephony + STT + LLM + TTS)
- **LLM**: OpenAI GPT-4o-mini (via Vapi)
- **Voice**: OpenAI TTS (alloy)

## Features

- 12 patient test scenarios covering edge cases, escalation paths, and standard flows
- 9 automatic bug detection patterns (hold loops, missing tickets, weekend bookings, failed escalations, record lookup failures, excessive verification, etc.)
- Full transcript recording with both patient and agent sides
- Background transcript polling — automatically fetches results after each call
- Bug reporting system with severity levels and recommendations
- React dashboard with Dashboard, Transcripts, and Bug Reports tabs

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- MongoDB (running locally or a cloud instance)
- [Vapi](https://vapi.ai) account with a phone number
- [ngrok](https://ngrok.com) (or any tunnel to expose localhost for Vapi webhooks)

### Backend

```bash
cd backend
pip install -r requirements.txt
```

Copy the example env and fill in your values:

```bash
cp .env.example .env
```

| Variable | Description |
|----------|-------------|
| `MONGO_URL` | MongoDB connection string |
| `DB_NAME` | Database name |
| `VAPI_API_KEY` | Your Vapi API key |
| `VAPI_PHONE_NUMBER_ID` | Your Vapi phone number ID |
| `BACKEND_URL` | Public URL for webhooks (e.g. ngrok URL) |

Start the server:

```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install --legacy-peer-deps
```

Copy the example env:

```bash
cp .env.example .env
```

Start the dev server:

```bash
npm start
```

### Expose Backend for Webhooks

Vapi needs to reach your backend. Use ngrok:

```bash
ngrok http 8000
```

Copy the `https://...ngrok-free.app` URL into `backend/.env` as `BACKEND_URL`.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/scenarios` | List all 12 test scenarios |
| GET | `/api/bug-patterns` | List auto-detection patterns |
| POST | `/api/call` | Initiate an outbound test call via Vapi |
| GET | `/api/calls` | List all call records |
| GET | `/api/calls/{id}` | Get a specific call |
| GET | `/api/calls/{id}/transcript` | Get call transcript + auto-detected bugs |
| GET | `/api/calls/{id}/vapi-transcript` | Force-fetch transcript from Vapi API |
| POST | `/api/bugs` | Create a manual bug report |
| GET | `/api/bugs` | List all bug reports |
| DELETE | `/api/bugs/{id}` | Delete a bug report |
| GET | `/api/config/status` | Check Vapi configuration status |

## Test Scenarios

| Category | Scenario | What It Tests |
|----------|----------|---------------|
| Edge Case | Sunday Appointment Trap | Booking on a closed day |
| Edge Case | Availability Timeout Probe | Hold loop / timeout handling |
| Edge Case | Off-Topic Guardrail Test | Scope boundaries |
| Escalation | Urgent Medication Refill | Emergency escalation paths |
| Escalation | Speak to Human Request | Human handoff handling |
| Standard | Ticket Number Demand | Documentation completeness |
| Standard | Beyond One Week Availability | Alternative scheduling |
| Standard | Insurance Verification | Coverage questions |
| Standard | Cancel and Rebook Same Call | State management |
| Standard | Interruption Handling | Context switching |
| Standard | Backache Triage | Symptom clarification |
| Standard | No Insurance Scenario | Self-pay handling |

## Bug Detection Patterns

| Pattern | Severity | Trigger |
|---------|----------|---------|
| Infinite Hold Loop | Critical | "please hold" / "let me check" 3+ times without results |
| Documented Without Reference | High | Claims documentation but no ticket number |
| Weekend Appointment Booked | High | Confirms Saturday/Sunday appointment |
| No Alternative Timeframe | Medium | Can't check availability, no alternatives offered |
| Technical Error Without Escalation | High | System error without concrete escalation path |
| Failed Escalation — No Alternative | High | Live transfer unavailable, no alternative contact given |
| Patient Record Not Found — No Recovery | Medium | Can't find record, doesn't offer to create one |
| Excessive Identity Verification | Medium | Asks for name/DOB/phone 4+ times before helping |
| No Symptom Clarification | Medium | Patient mentions symptoms, agent skips triage questions |

## Testing

```bash
python backend_test.py
```
# Pretty-Good-AI
