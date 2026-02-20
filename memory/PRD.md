# PGA Voice Bot - Product Requirements Document

## Original Problem Statement
Build a voice bot for Pretty Good AI's engineering challenge that calls +1-805-439-8008 and simulates patient conversations to test the Athena AI medical office agent. Requires Twilio for calls, Claude for dialogue generation, MongoDB for transcripts, and a React dashboard.

## Architecture
- **Backend**: FastAPI with Twilio voice integration and Google Gemini (gemini-1.5-flash) for patient dialogue
- **Frontend**: React dashboard with tabs for calls, transcripts, and bug reporting
- **Database**: MongoDB for storing calls, transcripts, and bug reports
- **Voice Flow**: Twilio outbound call → TwiML with Gather/Say → Gemini generates patient responses
- **Bug Detection**: Automatic pattern matching for common issues (hold loops, weekend bookings, missing tickets)

## User Personas
1. **QA Engineer**: Uses the bot to stress-test the Athena AI agent with edge cases
2. **Developer**: Reviews transcripts and bug reports to improve the AI agent

## Core Requirements
- [x] `/api/call` endpoint to trigger outbound calls to test number
- [x] `/api/voice/respond` webhook for Twilio voice handling
- [x] 12 patient scenarios (edge cases, escalations, standard flows)
- [x] Google Gemini (gemini-1.5-flash) for realistic patient dialogue with natural hesitations
- [x] MongoDB storage for calls and transcripts
- [x] Bug reporting system with severity levels + recommendations
- [x] React dashboard with 3 tabs (Dashboard, Transcripts, Bugs)
- [x] Automatic bug pattern detection (5 patterns)
- [x] Pre-seeded confirmed bug from manual testing

## What's Been Implemented (Feb 2026)

### Iteration 1 - MVP
- Complete FastAPI backend with Twilio integration
- Basic patient scenarios
- Claude-powered conversational AI
- Transcript recording and storage
- Bug reporting with severity tracking
- React dashboard with modern dark UI

### Iteration 2 - Enhanced Testing
- **12 new edge-case scenarios** based on real Athena testing:
  - Availability Timeout Probe, Sunday Appointment Trap, Ticket Number Demand
  - Beyond One Week Availability, Urgent Medication Refill, Speak to Human Request
  - Insurance Verification, Cancel and Rebook Same Call, Interruption Handling
  - Off-Topic Guardrail Test, Backache Triage, No Insurance Scenario
- **5 automatic bug detection patterns**:
  - Infinite Hold Loop (critical)
  - Documented Without Reference (high)
  - Weekend Appointment Booked (high)
  - No Alternative Timeframe (medium)
  - Technical Error Without Escalation (high)
- **Realistic patient persona**: Natural hesitations ("um", "uh"), pushback on vague answers, patience during holds
- **Seeded confirmed bug**: Infinite loading loop when checking multiple doctor availability
- **Aggressive Claude probing**: Evaluates whether to dig deeper vs. move on after each response

## Test Scenarios by Category
- **Edge Case**: Availability Timeout Probe, Sunday Appointment Trap, Off-Topic Guardrail Test
- **Escalation**: Urgent Medication Refill, Speak to Human Request
- **Standard**: Ticket Number Demand, Beyond One Week, Insurance, Cancel/Rebook, Interruption, Backache, No Insurance

## Environment Variables Required
- TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER
- ANTHROPIC_API_KEY
- BACKEND_URL (for webhooks)

## Next Tasks / Backlog
### P0 (Critical)
- User needs to add real Twilio/Anthropic credentials to make calls

### P1 (Important)
- Export transcripts to text files for submission
- Generate bug report summary document for PGA submission

### P2 (Nice to have)
- Call recording audio storage
- Batch call scheduling
- Transcript analysis report
